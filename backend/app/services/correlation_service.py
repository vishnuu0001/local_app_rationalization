import json
import datetime
from typing import Dict, List, Any, Tuple, Optional
from difflib import SequenceMatcher

from app import db
from app.models.corent_data import CorentData
from app.models.cast import CASTData, ApplicationInventory
from app.models.correlation import CorrelationResult, MasterMatrixEntry
from app.models.industry_data import IndustryData


class CorrelationService:
    """
    Service to correlate Corent (Infrastructure) and CAST (Code Analysis) extracted data.
    
    Primary matching strategy:
    - Uses APP ID as the primary key/relationship between the two databases
    - Direct APP ID matching provides high confidence correlations (1.0)
    - Fuzzy matching on app names used as fallback for unmatched items
    """
    
    # Matching confidence thresholds
    MIN_CONFIDENCE = 0.6
    HIGH_CONFIDENCE = 0.85
    DIRECT_MATCH_CONFIDENCE = 1.0  # For APP ID exact matches
    
    @staticmethod
    def get_corent_data() -> Dict[str, Any]:
        """
        Fetch Corent (Infrastructure) data - prioritizes IndustryData if available.
        Uses APP ID as primary identifier.
        
        Returns:
            Dictionary with structured infrastructure data indexed by APP ID
        """
        # Prioritize IndustryData if available
        industry_items = IndustryData.query.all()
        if industry_items:
            items = industry_items
            source = "Industry Templates"
        else:
            items = CorentData.query.all()
            source = "Corent"
        
        # Build CorentData mapping for lookups when using IndustryData
        corent_map = {item.app_id: item for item in CorentData.query.all()}
        
        data = {
            "source": source,
            "report_type": "infrastructure",
            "items_by_app_id": {},  # Indexed by APP ID for fast lookup
            "total_items": len(items),
            "tech_stack": {},
            "deployment_footprint": {},  # Geographic/environment distribution
            "server_app_mapping": [],  # For dashboard display
            "server_list": set()
        }
        
        for item in items:
            app_id = item.app_id
            
            # Get CorentData for this app if using IndustryData (for missing fields)
            corent_item = corent_map.get(app_id)
            
            # Handle both CorentData and IndustryData attributes
            entry = {
                "app_id": item.app_id,
                "app_name": item.app_name,
                "architecture_type": getattr(item, 'architecture_type', None),
                "business_owner": getattr(item, 'business_owner', None),
                "platform_host": getattr(item, 'platform_host', None),
                "server_type": getattr(item, 'server_type', None) or getattr(item, 'application_type', None),
                "operating_system": getattr(item, 'operating_system', None),
                "environment": getattr(item, 'environment', None),
                "cloud_suitability": getattr(item, 'cloud_suitability', None),
                "ha_dr_requirements": getattr(item, 'ha_dr_requirements', None),
                "installed_tech": getattr(item, 'server_type', None) or getattr(item, 'application_type', None),
                "server": getattr(item, 'platform_host', None) or "Unknown",
            }
            
            data["items_by_app_id"][app_id] = entry
            data["server_app_mapping"].append(entry)
            
            # Aggregate tech stack
            tech = entry["server_type"]
            if tech:
                data["tech_stack"][tech] = data["tech_stack"].get(tech, 0) + 1
            
            # Aggregate deployment footprint
            # Try to get from current item first, then fall back to CorentData
            deployment = getattr(item, 'deployment_geography', None) or getattr(item, 'environment', None)
            if not deployment and corent_item:
                deployment = getattr(corent_item, 'deployment_geography', None) or getattr(corent_item, 'environment', None)
            if deployment:
                data["deployment_footprint"][deployment] = data["deployment_footprint"].get(deployment, 0) + 1
            
            # Track servers
            server = getattr(item, 'platform_host', None)
            if server:
                data["server_list"].add(server)
        
        # Convert sets to lists for JSON serialization
        data["server_list"] = list(data["server_list"])
        
        return data
    
    @staticmethod
    def get_cast_data() -> Dict[str, Any]:
        """
        Fetch CAST (Code Analysis) data from CASTData and ApplicationInventory models.
        Uses APP ID as primary identifier.
        
        Returns:
            Dictionary with structured CAST data indexed by APP ID
        """
        cast_items = CASTData.query.all()
        app_inventories = ApplicationInventory.query.all()
        
        cast_data = {
            "source": "CAST",
            "report_type": "code_analysis",
            "items_by_app_id": {},  # Indexed by APP ID for fast lookup
            "total_items": len(cast_items),
            "programming_languages": {},
            "cloud_readiness_distribution": {},
            "repo_app_mapping": [],  # For dashboard display
            "architecture_components": [],  # For dashboard display
            "internal_dependencies": {}  # For dashboard display
        }
        
        # Load CAST Data (aggregated metrics)
        for item in cast_items:
            app_id = item.app_id
            
            # Get enriched data from IndustryData if available
            industry_item = IndustryData.query.filter_by(app_id=app_id).first()
            
            # Determine realistic programming language
            prog_language = CorrelationService.determine_programming_language(
                item.app_name,
                app_id,
                getattr(industry_item, 'application_type', None) if industry_item else None
            )
            
            cast_entry = {
                "app_id": item.app_id,
                "app_name": item.app_name,
                "application_architecture": item.application_architecture,
                "source_code_availability": item.source_code_availability,
                "programming_language": prog_language,  # Use determined language instead of "Unknown"
                "component_coupling": item.component_coupling,
                "cloud_suitability": item.cloud_suitability,
                "volume_external_dependencies": item.volume_external_dependencies,
                "code_design": item.code_design,
                "from_cast_data": True,
                "language": prog_language,  # For dashboard - use determined language
                "repo": f"repo/{item.app_id}",  # Generate repo path for dashboard
                "framework": item.application_architecture or "N/A",
            }
            
            cast_data["items_by_app_id"][app_id] = cast_entry
            
            # Add to both repo_app_mapping and architecture components for dashboard
            cast_data["repo_app_mapping"].append(cast_entry)
            cast_data["architecture_components"].append(cast_entry)
            
            # Aggregate programming languages - use the determined language
            cast_data["programming_languages"][prog_language] = cast_data["programming_languages"].get(prog_language, 0) + 1
            
            # Aggregate cloud readiness
            if item.cloud_suitability:
                cast_data["cloud_readiness_distribution"][item.cloud_suitability] = cast_data["cloud_readiness_distribution"].get(item.cloud_suitability, 0) + 1
            
            # Track dependencies
            if item.volume_external_dependencies:
                cast_data["internal_dependencies"][app_id] = {
                    "app_name": item.app_name,
                    "dependency_count": item.volume_external_dependencies
                }
        
        # Load ApplicationInventory (detailed code-level analysis)
        for item in app_inventories:
            app_id = item.app_id
            
            app_inv_entry = {
                "app_id": item.app_id,
                "app_name": item.application or item.app_id,
                "repository": item.repo,
                "repo": item.repo,  # For dashboard
                "primary_language": item.primary_language,
                "language": item.primary_language,  # For dashboard
                "framework": item.framework,
                "loc_k": item.loc_k,
                "modules": item.modules,
                "database": item.db_name,
                "external_integrations": item.ext_int,
                "quality": item.quality,
                "security": item.security,
                "cloud_ready": item.cloud_ready,
                "from_app_inventory": True,
                "type": "Microservice"  # Default type
            }
            
            # Merge with existing CAST data if present, otherwise create new entry
            if app_id in cast_data["items_by_app_id"]:
                cast_data["items_by_app_id"][app_id].update(app_inv_entry)
                # Update the architecture component as well
                for i, component in enumerate(cast_data["architecture_components"]):
                    if component["app_id"] == app_id:
                        component.update(app_inv_entry)
                        break
            else:
                cast_data["items_by_app_id"][app_id] = app_inv_entry
                cast_data["architecture_components"].append(app_inv_entry)
            
            # Add to repo mapping for dashboard
            cast_data["repo_app_mapping"].append(app_inv_entry)
        
        return cast_data
    
    
    @staticmethod
    def determine_programming_language(app_name: str, app_id: str, application_type: str = None) -> str:
        """
        Determine programming language based on app name patterns and type.
        Uses heuristics to assign realistic languages for test data.
        
        Args:
            app_name: Application name
            app_id: Application ID
            application_type: Type of application (e.g., "Commercial off the shelf")
            
        Returns:
            Programming language name
        """
        app_name_lower = app_name.lower()
        
        # Language patterns in app names
        if any(pattern in app_name_lower for pattern in ['php', 'laravel', 'wordpress']):
            return 'PHP'
        elif any(pattern in app_name_lower for pattern in ['python', 'django', 'flask']):
            return 'Python'
        elif any(pattern in app_name_lower for pattern in ['java', 'spring', 'tomcat']):
            return 'Java'
        elif any(pattern in app_name_lower for pattern in ['node', 'express', 'react', 'vue', 'javascript']):
            return 'JavaScript/Node.js'
        elif any(pattern in app_name_lower for pattern in ['.net', 'csharp', 'c#', 'aspnet', 'dotnet']):
            return 'C#/.NET'
        elif any(pattern in app_name_lower for pattern in ['go', 'golang']):
            return 'Go'
        elif any(pattern in app_name_lower for pattern in ['rust']):
            return 'Rust'
        elif any(pattern in app_name_lower for pattern in ['ruby', 'rails']):
            return 'Ruby'
        elif any(pattern in app_name_lower for pattern in ['cpp', 'c++', 'native']):
            return 'C++'
        elif any(pattern in app_name_lower for pattern in ['bitcoin', 'crypto', 'blockchain']):
            return 'Go'  # Popular for blockchain
        
        # Default based on application type
        if application_type:
            app_type_lower = application_type.lower()
            if 'commercial' in app_type_lower:
                if 'major' in app_type_lower:
                    return 'Java'  # Complex commercial systems often Java-based
                else:
                    return 'C#/.NET'  # Commercial systems often .NET
            elif 'self' in app_type_lower:
                return 'Python'  # Self-developed often Python
        
        # Distribute remaining apps across common languages
        hash_value = sum(ord(c) for c in app_id) % 5
        languages = ['Java', 'Python', 'C#/.NET', 'JavaScript/Node.js', 'Go']
        return languages[hash_value]
    
    @staticmethod
    def string_similarity(s1: str, s2: str) -> float:
        """
        Calculate string similarity score (0.0 - 1.0).
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Similarity score
        """
        s1 = str(s1).strip().lower()
        s2 = str(s2).strip().lower()
        
        if not s1 or not s2:
            return 0.0
        
        return SequenceMatcher(None, s1, s2).ratio()
    
    @staticmethod
    def correlate_data() -> Dict[str, Any]:
        """
        Correlate data from ALL THREE sources: Industry, Corent, and CAST data.
        
        Strategy:
        1. Combine IndustryData + CorentData as the infrastructure layer (all records from both)
        2. Get CAST data for code analysis layer
        3. Attempt to match records by APP ID first, then by name similarity
        
        Returns:
            Dictionary with correlation results from all three data sources
        """
        # Get infrastructure data from BOTH Industry and Corent
        industry_items = IndustryData.query.all()
        corent_items = CorentData.query.all()
        cast_items = CASTData.query.all()
        
        # Build combined infrastructure data structure
        infra_data = {
            "source": "Industry + Corent",
            "report_type": "infrastructure",
            "items_by_app_id": {},
            "total_items": len(industry_items) + len(corent_items),
            "tech_stack": {},
            "deployment_footprint": {},
            "server_app_mapping": [],
            "server_list": set()
        }
        
        # Add all IndustryData records
        for item in industry_items:
            app_id = item.app_id
            entry = {
                "app_id": item.app_id,
                "app_name": item.app_name,
                "architecture_type": getattr(item, 'architecture_type', None),
                "business_owner": getattr(item, 'business_owner', None),
                "platform_host": getattr(item, 'platform_host', None),
                "server_type": getattr(item, 'server_type', None) or getattr(item, 'application_type', None),
                "operating_system": getattr(item, 'operating_system', None),
                "environment": getattr(item, 'environment', None),
                "cloud_suitability": getattr(item, 'cloud_suitability', None),
                "ha_dr_requirements": getattr(item, 'ha_dr_requirements', None),
                "installed_tech": getattr(item, 'server_type', None) or getattr(item, 'application_type', None),
                "server": getattr(item, 'platform_host', None) or "Unknown",
                "source": "IndustryData"
            }
            infra_data["items_by_app_id"][app_id] = entry
            infra_data["server_app_mapping"].append(entry)
        
        # Add all CorentData records (won't duplicate since app_ids should be different)
        for item in corent_items:
            app_id = item.app_id
            if app_id not in infra_data["items_by_app_id"]:  # Avoid duplicates
                entry = {
                    "app_id": item.app_id,
                    "app_name": item.app_name,
                    "architecture_type": item.architecture_type,
                    "business_owner": item.business_owner,
                    "platform_host": item.platform_host,
                    "server_type": item.server_type,
                    "operating_system": item.operating_system,
                    "environment": item.environment,
                    "cloud_suitability": item.cloud_suitability,
                    "ha_dr_requirements": item.ha_dr_requirements,
                    "installed_tech": item.server_type,
                    "server": item.platform_host or "Unknown",
                    "source": "CorentData"
                }
                infra_data["items_by_app_id"][app_id] = entry
                infra_data["server_app_mapping"].append(entry)
        
        # Update total_items to reflect actual deduplicated count
        infra_data["total_items"] = len(infra_data["items_by_app_id"])
        
        # Build CAST data structure
        cast_data = {
            "source": "CAST",
            "report_type": "code_analysis",
            "items_by_app_id": {},
            "total_items": len(cast_items),
            "programming_languages": {},
            "cloud_readiness_distribution": {},
            "repo_app_mapping": [],
            "architecture_components": [],
            "internal_dependencies": {}
        }
        
        for item in cast_items:
            app_id = item.app_id
            
            # Get application_type from IndustryData for language determination
            industry_item = IndustryData.query.filter_by(app_id=app_id).first()
            app_type = industry_item.application_type if industry_item else None
            
            # Determine intelligent programming language instead of "Unknown"
            determined_language = CorrelationService.determine_programming_language(
                item.app_name, 
                item.app_id, 
                app_type
            )
            
            cast_entry = {
                "app_id": item.app_id,
                "app_name": item.app_name,
                "application_architecture": item.application_architecture,
                "source_code_availability": item.source_code_availability,
                "programming_language": determined_language,
                "component_coupling": item.component_coupling,
                "cloud_suitability": item.cloud_suitability,
                "volume_external_dependencies": item.volume_external_dependencies,
                "code_design": item.code_design,
                "from_cast_data": True,
                "language": determined_language,
                "repo": f"repo/{item.app_id}",  # Generate repo path for dashboard
                "framework": item.application_architecture or "N/A",
            }
            cast_data["items_by_app_id"][app_id] = cast_entry
            cast_data["repo_app_mapping"].append(cast_entry)
            cast_data["architecture_components"].append(cast_entry)
            
            if determined_language:
                cast_data["programming_languages"][determined_language] = cast_data["programming_languages"].get(determined_language, 0) + 1
            
            if item.cloud_suitability:
                cast_data["cloud_readiness_distribution"][item.cloud_suitability] = cast_data["cloud_readiness_distribution"].get(item.cloud_suitability, 0) + 1
            
            if item.volume_external_dependencies:
                cast_data["internal_dependencies"][app_id] = {
                    "app_name": item.app_name,
                    "dependency_count": item.volume_external_dependencies
                }
        
        # Now correlate infrastructure + CAST data
        direct_matches = []  # APP ID exact matches
        fuzzy_matches = []   # Name-based matches
        matched_infra_app_ids = set()
        matched_cast_app_ids = set()
        
        # PHASE 1: Direct matching using APP ID
        for app_id, infra_item in infra_data["items_by_app_id"].items():
            if app_id in cast_data["items_by_app_id"]:
                cast_item = cast_data["items_by_app_id"][app_id]
                
                match_entry = {
                    "infra_item": infra_item,
                    "cast_item": cast_item,
                    "confidence": CorrelationService.DIRECT_MATCH_CONFIDENCE,
                    "matching_criteria": ["Direct APP ID match"],
                    "confidence_level": "high",
                    "app_id": app_id,
                    "match_type": "direct"
                }
                
                direct_matches.append(match_entry)
                matched_infra_app_ids.add(app_id)
                matched_cast_app_ids.add(app_id)
        
        # PHASE 2: Fuzzy matching on app_name for remaining items
        unmatched_infra = {
            app_id: item for app_id, item in infra_data["items_by_app_id"].items()
            if app_id not in matched_infra_app_ids
        }
        unmatched_cast = {
            app_id: item for app_id, item in cast_data["items_by_app_id"].items()
            if app_id not in matched_cast_app_ids
        }
        
        # Fuzzy match remaining items
        for infra_app_id, infra_item in list(unmatched_infra.items()):
            best_match = None
            best_confidence = 0.0
            best_cast_app_id = None
            
            for cast_app_id, cast_item in unmatched_cast.items():
                name_sim = CorrelationService.string_similarity(
                    infra_item.get("app_name", ""),
                    cast_item.get("app_name", "")
                )
                
                if name_sim >= CorrelationService.MIN_CONFIDENCE and name_sim > best_confidence:
                    best_match = cast_item
                    best_confidence = name_sim
                    best_cast_app_id = cast_app_id
            
            if best_match:
                match_entry = {
                    "infra_item": infra_item,
                    "cast_item": best_match,
                    "confidence": round(best_confidence, 3),
                    "matching_criteria": [f"App name match ({best_confidence:.2f})"],
                    "confidence_level": "medium" if best_confidence >= 0.8 else "low",
                    "app_id": infra_app_id,
                    "match_type": "fuzzy"
                }
                
                fuzzy_matches.append(match_entry)
                del unmatched_infra[infra_app_id]
                del unmatched_cast[best_cast_app_id]
        
        correlation_layer = direct_matches + fuzzy_matches
        
        return {
            "corent_dashboard": infra_data,
            "cast_dashboard": cast_data,
            "correlation_layer": correlation_layer,
            "direct_matches": direct_matches,
            "fuzzy_matches": fuzzy_matches,
            "unmatched_corent": list(unmatched_infra.values()),
            "unmatched_cast": list(unmatched_cast.values()),
            "statistics": {
                "corent_total": len(infra_data["items_by_app_id"]),
                "cast_total": cast_data["total_items"],
                "direct_matched": len(direct_matches),
                "fuzzy_matched": len(fuzzy_matches),
                "total_matched": len(correlation_layer),
                "unmatched_corent_count": len(unmatched_infra),
                "unmatched_cast_count": len(unmatched_cast),
                "match_percentage": round(
                    (len(correlation_layer) / max(len(infra_data["items_by_app_id"]), 1)) * 100, 2
                )
            }
        }

    
    @staticmethod
    def generate_master_matrix(correlation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate master matrix combining Corent and CAST data.
        
        Master matrix columns:
        - App Name: Application identifier
        - Infrastructure: Server/hostname from Corent
        - Server Type: Domain/environment from Corent
        - Installed App: Application name from Corent
        - App Component: Framework/language from CAST
        - Repository: Code repository from CAST
        - Cloud Suitability: Cloud readiness from both sources
        - Confidence: Correlation confidence score (1.0 for direct APP ID match)
        
        Args:
            correlation_data: Output from correlate_data()
            
        Returns:
            List of master matrix entries with complete app information
        """
        master_matrix = []
        
        # Process all matched items (both direct and fuzzy matches)
        for match in correlation_data.get("correlation_layer", []):
            infra = match["infra_item"]
            cast = match["cast_item"]
            
            # Get repository - check both "repository" and "repo" fields
            repository = cast.get("repository", "") or cast.get("repo", "")
            
            entry = {
                "app_id": match.get("app_id", ""),
                "app_name": infra.get("app_name", "") or cast.get("app_name", ""),
                "infrastructure": infra.get("platform_host", ""),
                "server_type": infra.get("server_type", ""),
                "installed_app": infra.get("app_name", ""),
                "environment": infra.get("environment", ""),
                "app_component": f"{cast.get('programming_language', '')} - {cast.get('framework', '')}".strip(" - "),
                "repository": repository,
                "business_owner": infra.get("business_owner", ""),
                "cloud_suitability_corent": infra.get("cloud_suitability", ""),
                "cloud_suitability_cast": cast.get("cloud_suitability", ""),
                "confidence": match["confidence"],
                "confidence_level": match["confidence_level"],
                "match_type": match.get("match_type", "unknown"),
                "matching_criteria": " | ".join(match["matching_criteria"])
            }
            entry["infra"] = entry["infrastructure"]
            entry["server"] = entry["server_type"]
            entry["repo"] = entry["repository"]
            master_matrix.append(entry)
        
        # Add unmatched Infrastructure items with "Unmatched from Infrastructure" indicator
        for infra_item in correlation_data.get("unmatched_infra", []):
            entry = {
                "app_id": infra_item.get("app_id", ""),
                "app_name": infra_item.get("app_name", ""),
                "infrastructure": infra_item.get("platform_host", ""),
                "server_type": infra_item.get("server_type", ""),
                "installed_app": infra_item.get("app_name", ""),
                "environment": infra_item.get("environment", ""),
                "app_component": "Unmatched - No CAST data",
                "repository": "",
                "business_owner": infra_item.get("business_owner", ""),
                "cloud_suitability_corent": infra_item.get("cloud_suitability", ""),
                "cloud_suitability_cast": "",
                "confidence": 0.0,
                "confidence_level": "unmatched",
                "match_type": "unmatched",
                "matching_criteria": "No CAST correlation found"
            }
            entry["infra"] = entry["infrastructure"]
            entry["server"] = entry["server_type"]
            entry["repo"] = entry["repository"]
            master_matrix.append(entry)
        
        # Add unmatched CAST items with "Unmatched from CAST" indicator
        for cast_item in correlation_data.get("unmatched_cast", []):
            # Get repository - check both "repository" and "repo" fields
            repository = cast_item.get("repository", "") or cast_item.get("repo", "")
            
            entry = {
                "app_id": cast_item.get("app_id", ""),
                "app_name": cast_item.get("app_name", ""),
                "infrastructure": "",
                "server_type": "",
                "installed_app": "",
                "environment": "",
                "app_component": f"{cast_item.get('programming_language', '')} - {cast_item.get('framework', '')}".strip(" - "),
                "repository": repository,
                "business_owner": "",
                "cloud_suitability_corent": "",
                "cloud_suitability_cast": cast_item.get("cloud_suitability", ""),
                "confidence": 0.0,
                "confidence_level": "unmatched",
                "match_type": "unmatched",
                "matching_criteria": "No Corent correlation found"
            }
            entry["infra"] = entry["infrastructure"]
            entry["server"] = entry["server_type"]
            entry["repo"] = entry["repository"]
            master_matrix.append(entry)
        
        return master_matrix
    
    @classmethod
    def create_correlation_result(cls, correlation_data: Dict[str, Any]) -> CorrelationResult:
        """
        Create and store correlation result in database.
        
        Args:
            correlation_data: Output from correlate_data()
            
        Returns:
            CorrelationResult database object with stored master matrix entries
        """
        master_matrix = cls.generate_master_matrix(correlation_data)
        
        # Create main correlation result record
        result = CorrelationResult(
            correlation_data=json.dumps(correlation_data, default=str),
            master_matrix=json.dumps(master_matrix, default=str),
            matched_count=correlation_data.get("statistics", {}).get("total_matched", 0),
            total_count=correlation_data.get("statistics", {}).get("corent_total", 0),
            match_percentage=correlation_data.get("statistics", {}).get("match_percentage", 0.0)
        )
        
        db.session.add(result)
        db.session.flush()  # Get the ID before adding child records
        
        # Store individual master matrix entries
        for entry_data in master_matrix:
            entry = MasterMatrixEntry(
                correlation_result_id=result.id,
                app_name=entry_data.get("app_name", ""),
                infra=entry_data.get("infrastructure", ""),
                server=entry_data.get("server_type", ""),
                installed_app=entry_data.get("installed_app", ""),
                app_component=entry_data.get("app_component", ""),
                repo=entry_data.get("repository", ""),
                confidence=entry_data.get("confidence", 0.0),
                entry_data=json.dumps(entry_data, default=str)
            )
            db.session.add(entry)
        
        db.session.commit()
        
        return result
    @staticmethod
    def enrich_item_with_multi_db_data(item: Any, app_id: str) -> Dict[str, Any]:
        """Enrich an item with data from multiple databases for missing fields.
        
        Strategy: For removed columns from CAST, lookup from IndustryData then CorentData
        
        Args:
            item: The item to enrich (any model)
            app_id: The application ID to lookup
            
        Returns:
            Dictionary with enriched fields including application_type and capabilities
        """
        enriched = {}
        
        # Start with direct attributes from item
        if hasattr(item, '__dict__'):
            enriched = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
        elif isinstance(item, dict):
            enriched = item.copy()
        
        # Try to get application_type and capabilities from IndustryData first
        try:
            industry_item = IndustryData.query.filter_by(app_id=app_id).first()
            if industry_item:
                enriched['application_type'] = getattr(industry_item, 'application_type', None) or enriched.get('application_type')
                enriched['capabilities'] = getattr(industry_item, 'capabilities', None) or enriched.get('capabilities')
                return enriched
        except Exception:
            pass
        
        # Fall back to CorentData
        try:
            corent_item = CorentData.query.filter_by(app_id=app_id).first()
            if corent_item:
                enriched['application_type'] = getattr(corent_item, 'application_type', None) or enriched.get('application_type')
                enriched['capabilities'] = getattr(corent_item, 'capabilities', None) or enriched.get('capabilities')
                return enriched
        except Exception:
            pass
        
        return enriched