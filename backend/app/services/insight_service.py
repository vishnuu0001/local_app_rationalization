"""
Insight Service - Provides comprehensive dashboard data and analytics

This service generates actionable insights from infrastructure (Corent), 
code analysis (CAST), and application inventory data, regardless of 
correlation status.

Features:
- Dashboard metrics (KPIs, statistics, trends)
- Data quality assessment
- Risk analysis
- Technology stack insights
- Cloud readiness evaluation
- Cost and complexity analysis
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime

from app import db
from app.models.corent_data import CorentData
from app.models.cast import CASTData, ApplicationInventory
from app.models.correlation import CorrelationResult
from app.models.industry_data import IndustryData


class InsightService:
    """Service to generate comprehensive dashboard insights and analytics"""
    
    @staticmethod
    def get_dashboard_insights() -> Dict[str, Any]:
        """
        Generate complete dashboard insights including metrics, analysis, and recommendations.
        
        Prioritizes IndustryData (uploaded Industry Templates) over Corent/CAST data.
        
        Returns:
            Dictionary with:
            - summary: Key metrics and KPIs
            - infrastructure_insights: Analysis based on available data
            - code_insights: CAST analysis  
            - correlation_insights: Correlation analysis if available
            - dashboard_data: Pre-formatted data for UI components
            - recommendations: Actionable insights
        """
        # Check if IndustryData has records - prioritize it
        industry_items = IndustryData.query.all()
        corent_items = []
        cast_items = []
        app_inv_items = []
        
        if not industry_items:
            # Fall back to Corent/CAST if no Industry data
            corent_items = CorentData.query.all()
            cast_items = CASTData.query.all()
        else:
            # Use Industry data exclusively when available
            corent_items = industry_items
        
        latest_correlation = CorrelationResult.query.order_by(
            CorrelationResult.created_at.desc()
        ).first()
        
        infrastructure_insights = InsightService._analyze_infrastructure(corent_items)
        code_insights = InsightService._analyze_code(cast_items, app_inv_items)
        correlation_insights = InsightService._analyze_correlation(latest_correlation)
        risk_assessment = InsightService._assess_risks(corent_items, cast_items, app_inv_items)
        
        # When IndustryData is used (cast_items empty), derive code metrics from correlation layer
        code_app_count = len(cast_items)
        prog_lang_count = len(code_insights['programming_languages'])
        if code_app_count == 0 and latest_correlation:
            import json as _json
            from collections import Counter as _Counter
            try:
                corr_data = (
                    _json.loads(latest_correlation.correlation_data)
                    if isinstance(latest_correlation.correlation_data, str)
                    else latest_correlation.correlation_data
                )
                corr_layer = corr_data.get('correlation_layer', [])
                cast_entries = [c['cast_item'] for c in corr_layer if c.get('cast_item')]
                code_app_count = len(cast_entries)

                # Build language counts
                lang_counter = _Counter(
                    e.get('language') or e.get('programming_language', '')
                    for e in cast_entries
                    if e.get('language') or e.get('programming_language')
                )
                prog_lang_count = len(lang_counter)

                # Build architecture components list
                arch_components = [
                    {
                        'app_id': e.get('app_id', ''),
                        'app_name': e.get('app_name', ''),
                        'language': e.get('language') or e.get('programming_language') or 'Unknown',
                        'cloud_suitability': e.get('cloud_suitability', ''),
                        'source_code': e.get('source_code_availability', ''),
                        'type': e.get('application_architecture', 'Unknown'),
                        'component_coupling': e.get('component_coupling', 'N/A')
                    }
                    for e in cast_entries
                ]

                # Build internal dependencies
                int_deps = {}
                for e in cast_entries:
                    vol = e.get('volume_external_dependencies')
                    if vol:
                        try:
                            dep_count = int(vol)
                        except (ValueError, TypeError):
                            dep_count = vol
                        int_deps[e.get('app_id', '')] = {
                            'app_name': e.get('app_name', e.get('app_id', '')),
                            'dependency_count': dep_count
                        }

                # Rebuild repo_app_mapping
                repo_mapping = [
                    {
                        'app_id': e.get('app_id', ''),
                        'app_name': e.get('app_name', e.get('app_id', '')),
                        'repo': e.get('repo', 'Unknown'),
                        'language': e.get('language') or e.get('programming_language') or 'Unknown',
                        'framework': e.get('framework') or e.get('application_architecture') or 'Unknown',
                        'loc_k': e.get('loc_k', 0),
                        'quality_score': e.get('code_design', 0),
                        'cloud_ready': (e.get('cloud_suitability') or '').lower() in ('high', 'yes', 'cloud-ready')
                    }
                    for e in cast_entries
                ]

                # Update code_insights in-place with correlation-derived data
                code_insights = {
                    'total_cast_items': code_app_count,
                    'total_inventory_items': len(app_inv_items),
                    'programming_languages': dict(lang_counter.most_common()),
                    'cloud_readiness': {},
                    'component_coupling': {},
                    'total_items': code_app_count,
                    'dashboard_format': {
                        'programming_languages': dict(lang_counter.most_common()),
                        'repo_app_mapping': repo_mapping,
                        'architecture_components': arch_components,
                        'internal_dependencies': int_deps
                    }
                }
            except Exception:
                pass

        total_servers = len(set(c.platform_host for c in corent_items if c.platform_host))

        # Generate summary metrics
        summary = {
            'total_applications': len(set(i.app_id for i in corent_items)),
            'infrastructure_applications': len(corent_items),
            'code_applications': code_app_count,
            'application_inventory_items': len(app_inv_items),
            'correlation_status': 'completed' if latest_correlation else 'not_started',
            'matched_applications': (
                latest_correlation.matched_count if latest_correlation else 0
            ),
            'match_percentage': (
                latest_correlation.match_percentage if latest_correlation else 0.0
            ),
            'data_quality_score': InsightService._calculate_data_quality_score(
                corent_items, cast_items, app_inv_items
            ),
            'total_servers': total_servers,
            'unique_servers': total_servers,  # alias for frontend compatibility
            'unique_technologies': len(infrastructure_insights['tech_stack']),
            'programming_languages': prog_lang_count,
            'high_risk_applications': risk_assessment['high_risk_count'],
            'cloud_ready_percentage': risk_assessment['cloud_ready_percentage'],
            'estimated_annual_maintenance': InsightService._estimate_maintenance_cost(
                corent_items, app_inv_items
            ),
            'data_source': 'Industry Templates' if industry_items else 'Corent/CAST Data'
        }
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': summary,
            'infrastructure_insights': infrastructure_insights,
            'code_insights': code_insights,
            'correlation_insights': correlation_insights,
            'risk_assessment': risk_assessment,
            'dashboard_data': {
                'corent': infrastructure_insights.get('dashboard_format', {}),
                'cast': code_insights.get('dashboard_format', {}),
                'correlation': correlation_insights.get('dashboard_format', {})
            },
            'recommendations': InsightService._generate_recommendations(
                infrastructure_insights,
                code_insights,
                risk_assessment,
                summary
            ),
            'data_sources': {
                'corent_populated': len(corent_items) > 0,
                'cast_populated': len(cast_items) > 0,
                'app_inventory_populated': len(app_inv_items) > 0,
                'correlation_available': latest_correlation is not None
            }
        }
    
    @staticmethod
    def _analyze_infrastructure(items: List) -> Dict[str, Any]:
        """Analyze infrastructure data (Corent or IndustryData)"""
        if not items:
            return {
                'total_items': 0,
                'tech_stack': {},
                'deployment_footprint': {},
                'environments': {},
                'cloud_suitability_distribution': {},
                'server_utilization': {},
                'dashboard_format': {
                    'server_app_mapping': [],
                    'tech_stack': {},
                    'deployment_footprint': {}
                }
            }
        
        tech_stack = Counter(getattr(item, 'server_type', None) or getattr(item, 'application_type', None) 
                           for item in items 
                           if getattr(item, 'server_type', None) or getattr(item, 'application_type', None))
        environments = Counter(getattr(item, 'environment', None) for item in items 
                             if getattr(item, 'environment', None))
        cloud_suitability = Counter(getattr(item, 'cloud_suitability', None) for item in items 
                                   if getattr(item, 'cloud_suitability', None))
        deployment_footprint = Counter(
            getattr(item, 'deployment_geography', None) or getattr(item, 'environment', None)
            for item in items 
            if getattr(item, 'deployment_geography', None) or getattr(item, 'environment', None)
        )
        
        server_app_mapping = [
            {
                'app_id': item.app_id,
                'app_name': item.app_name,
                'server': getattr(item, 'platform_host', None) or 'Unknown',
                'server_type': getattr(item, 'server_type', None) or getattr(item, 'application_type', None) or 'Unknown',
                'environment': getattr(item, 'environment', None) or 'Unknown',
                'os': getattr(item, 'operating_system', None),
                'cloud_suitability': getattr(item, 'cloud_suitability', None),
                'business_owner': getattr(item, 'business_owner', None),
                'ha_dr': getattr(item, 'ha_dr_requirements', None) or 'None'
            }
            for item in items
        ]
        
        return {
            'total_items': len(items),
            'tech_stack': dict(tech_stack.most_common()),
            'environments': dict(environments),
            'deployment_footprint': dict(deployment_footprint),
            'cloud_suitability_distribution': dict(cloud_suitability),
            'unique_servers': len(set(i.platform_host for i in items if i.platform_host)),
            'dashboard_format': {
                'server_app_mapping': server_app_mapping,
                'tech_stack': dict(tech_stack.most_common()),
                'deployment_footprint': dict(deployment_footprint)
            }
        }
    
    @staticmethod
    def _analyze_code(cast_items: List[CASTData], app_inv_items: List[ApplicationInventory]) -> Dict[str, Any]:
        """Analyze code (CAST) data and application inventory"""
        if not cast_items:
            return {
                'total_items': 0,
                'programming_languages': {},
                'cloud_readiness': {},
                'component_coupling': {},
                'dashboard_format': {
                    'repo_app_mapping': [],
                    'architecture_components': [],
                    'internal_dependencies': {}
                }
            }
        
        languages = Counter(item.programming_language for item in cast_items if item.programming_language)
        cloud_readiness = Counter(item.cloud_suitability for item in cast_items if item.cloud_suitability)
        
        # Build architecture components
        architecture_components = [
            {
                'app_id': item.app_id,
                'app_name': item.app_name,
                'language': item.programming_language or 'Unknown',
                'cloud_suitability': item.cloud_suitability,
                'source_code': item.source_code_availability,
                'component_coupling': item.component_coupling
            }
            for item in cast_items
        ]
        
        # Build internal dependencies
        internal_dependencies = {}
        for item in cast_items:
            if item.volume_external_dependencies:
                dep_count = int(item.volume_external_dependencies) if isinstance(item.volume_external_dependencies, str) and item.volume_external_dependencies.isdigit() else item.volume_external_dependencies
                internal_dependencies[item.app_id] = {
                    'app_name': item.app_name,
                    'dependency_count': dep_count
                }
        
        # Build repo app mapping from app inventory
        repo_app_mapping = [
            {
                'app_id': item.app_id,
                'app_name': item.application or item.app_id,
                'repo': item.repo or 'Unknown',
                'language': item.primary_language or 'Unknown',
                'framework': item.framework or 'Unknown',
                'loc_k': item.loc_k or 0,
                'quality_score': item.quality or 0,
                'security_score': item.security or 0,
                'cloud_ready': item.cloud_ready or False
            }
            for item in app_inv_items
        ]
        
        return {
            'total_cast_items': len(cast_items),
            'total_inventory_items': len(app_inv_items),
            'programming_languages': dict(languages.most_common()),
            'application_types': {},
            'cloud_readiness_distribution': dict(cloud_readiness),
            'average_components_coupling': (
                sum(
                    float(item.component_coupling) if isinstance(item.component_coupling, str) and item.component_coupling.replace('.', '', 1).isdigit() else 0
                    for item in cast_items
                ) / len(cast_items)
                if cast_items else 0
            ),
            'total_external_dependencies': sum(
                int(item.volume_external_dependencies) if isinstance(item.volume_external_dependencies, str) and item.volume_external_dependencies.isdigit() else 0
                for item in cast_items
            ),
            'dashboard_format': {
                'repo_app_mapping': repo_app_mapping,
                'architecture_components': architecture_components,
                'internal_dependencies': internal_dependencies
            }
        }
    
    @staticmethod
    def _analyze_correlation(result: CorrelationResult) -> Dict[str, Any]:
        """Analyze correlation results if available"""
        if not result:
            return {
                'status': 'not_available',
                'message': 'No correlation has been run yet',
                'dashboard_format': {
                    'correlation_layer': [],
                    'match_statistics': {}
                }
            }
        
        import json
        try:
            correlation_data = (
                json.loads(result.correlation_data)
                if isinstance(result.correlation_data, str)
                else result.correlation_data
            )
            
            return {
                'status': 'completed',
                'matched_count': result.matched_count,
                'total_count': result.total_count,
                'match_percentage': result.match_percentage,
                'created_at': result.created_at.isoformat(),
                'correlation_layer': correlation_data.get('correlation_layer', []),
                'direct_matches': len(correlation_data.get('direct_matches', [])),
                'fuzzy_matches': len(correlation_data.get('fuzzy_matches', [])),
                'unmatched_corent': len(correlation_data.get('unmatched_corent', [])),
                'unmatched_cast': len(correlation_data.get('unmatched_cast', [])),
                'statistics': correlation_data.get('statistics', {}),
                'dashboard_format': {
                    'correlation_layer': correlation_data.get('correlation_layer', []),
                    'match_statistics': {
                        'direct_matches': len(correlation_data.get('direct_matches', [])),
                        'fuzzy_matches': len(correlation_data.get('fuzzy_matches', [])),
                        'unmatched_total': (
                            len(correlation_data.get('unmatched_corent', [])) +
                            len(correlation_data.get('unmatched_cast', []))
                        )
                    }
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error parsing correlation: {str(e)}',
                'dashboard_format': {}
            }
    
    @staticmethod
    def _assess_risks(
        items: List,
        cast_items: List[CASTData],
        app_inv_items: List[ApplicationInventory]
    ) -> Dict[str, Any]:
        """Assess risks across applications (handles both Corent and IndustryData)"""
        
        high_risk_count = 0
        cloud_ready_count = 0
        
        # Assess infrastructure data risks (Corent or IndustryData)
        for item in items:
            risk_score = 0
            
            # Legacy systems on outdated infrastructure
            server_type = getattr(item, 'server_type', None)
            if server_type and 'legacy' in str(server_type).lower():
                risk_score += 2
            
            # Missing HA/DR requirements
            ha_dr = getattr(item, 'ha_dr_requirements', None)
            if not ha_dr or str(ha_dr) == 'None':
                risk_score += 1
            
            # Not cloud suitable
            cloud_suitability = getattr(item, 'cloud_suitability', None)
            if cloud_suitability and 'not' in str(cloud_suitability).lower():
                risk_score += 1
            else:
                cloud_ready_count += 1
            
            if risk_score >= 2:
                high_risk_count += 1
        
        # Assess CAST data risks
        for item in cast_items:
            source_code = getattr(item, 'source_code_availability', None)
            if not source_code or str(source_code) == 'Not Available':
                high_risk_count += 1
        
        # Assess application inventory risks
        for item in app_inv_items:
            quality_val = getattr(item, 'quality', None)
            quality_val = quality_val if isinstance(quality_val, (int, float)) else 0
            if quality_val and quality_val < 50:
                high_risk_count += 1
        
        total_apps = len(items) + len(set(
            c.app_id for c in cast_items if c.app_id not in [r.app_id for r in items]
        ))
        
        cloud_ready_percentage = (
            (cloud_ready_count / total_apps * 100) if total_apps > 0 else 0
        )
        
        return {
            'high_risk_applications': high_risk_count,
            'high_risk_count': high_risk_count,
            'cloud_ready_count': cloud_ready_count,
            'cloud_ready_percentage': round(cloud_ready_percentage, 1),
            'risk_distribution': {
                'high': high_risk_count,
                'medium': max(0, len(items) // 2 - high_risk_count) if items else 0,
                'low': max(0, len(items) // 2) if items else 0
            },
            'key_risks': InsightService._identify_key_risks(items, cast_items)
        }
    
    @staticmethod
    def _identify_key_risks(
        items: List,
        cast_items: List[CASTData]
    ) -> List[str]:
        """Identify and prioritize key risks - works with Corent or IndustryData"""
        risks = []
        
        legacy_count = len([i for i in items if getattr(i, 'server_type', None) and 'legacy' in str(getattr(i, 'server_type', '')).lower()])
        if legacy_count > 0:
            risks.append(f'{legacy_count} legacy systems require modernization')
        
        no_ha_dr = len([i for i in items if not getattr(i, 'ha_dr_requirements', None) or str(getattr(i, 'ha_dr_requirements', None)) == 'None'])
        if no_ha_dr > 0:
            risks.append(f'{no_ha_dr} applications lack HA/DR protection')
        
        no_source_code = len([i for i in cast_items if not getattr(i, 'source_code_availability', None) or str(getattr(i, 'source_code_availability', None)) == 'Not Available'])
        if no_source_code > 0:
            risks.append(f'{no_source_code} applications have limited source code access')
        
        complex_deps = len([
            i for i in cast_items 
            if getattr(i, 'volume_external_dependencies', None) and (
                int(i.volume_external_dependencies) if isinstance(i.volume_external_dependencies, str) and i.volume_external_dependencies.isdigit() 
                else i.volume_external_dependencies
            ) > 10
        ])
        if complex_deps > 0:
            risks.append(f'{complex_deps} applications have high dependency complexity')
        
        return risks[:5]  # Top 5 risks
    
    @staticmethod
    @staticmethod
    def _calculate_data_quality_score(
        items: List,
        cast_items: List[CASTData],
        app_inv_items: List[ApplicationInventory]
    ) -> float:
        """Calculate overall data quality score (0-100) - works with Corent or IndustryData"""
        scores = []
        
        # Infrastructure data completeness (Corent or IndustryData)
        if items:
            completeness = sum(
                1 if getattr(item, 'app_id', None) and getattr(item, 'app_name', None) 
                    and (getattr(item, 'server_type', None) or getattr(item, 'application_type', None))
                else 0
                for item in items
            ) / len(items) * 100
            scores.append(completeness)
        
        # CAST completeness
        if cast_items:
            completeness = sum(
                1 if getattr(item, 'app_id', None) and getattr(item, 'app_name', None) 
                    and getattr(item, 'programming_language', None)
                else 0
                for item in cast_items
            ) / len(cast_items) * 100
            scores.append(completeness)
        
        # App Inventory completeness
        if app_inv_items:
            completeness = sum(
                1 if getattr(item, 'app_id', None) and getattr(item, 'application', None) 
                    and getattr(item, 'repo', None)
                else 0
                for item in app_inv_items
            ) / len(app_inv_items) * 100
            scores.append(completeness)
        
        return round(sum(scores) / len(scores), 1) if scores else 0.0
    
    @staticmethod
    def _estimate_maintenance_cost(
        items: List,
        app_inv_items: List[ApplicationInventory]
    ) -> float:
        """Estimate annual maintenance cost based on application profile"""
        # Base cost model: €50k per legacy app, €30k per standard app, €15k per cloud-ready
        total_cost = 0.0
        
        for item in items:
            server_type = getattr(item, 'server_type', None)
            cloud_suitability = getattr(item, 'cloud_suitability', None)
            
            if server_type and 'legacy' in str(server_type).lower():
                total_cost += 50000
            elif cloud_suitability and 'high' in str(cloud_suitability).lower():
                total_cost += 15000
            else:
                total_cost += 30000
        
        return total_cost
    
    @staticmethod
    def _generate_recommendations(
        infrastructure_insights: Dict[str, Any],
        code_insights: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        summary: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Infrastructure recommendations
        if summary['unique_technologies'] > 5:
            recommendations.append({
                'category': 'Infrastructure',
                'priority': 'high',
                'recommendation': f'Consolidate {summary["unique_technologies"]} different technologies to reduce complexity',
                'impact': 'Reduce operational overhead and training costs'
            })
        
        # Code insights recommendations
        if summary['programming_languages'] > 3:
            recommendations.append({
                'category': 'Development',
                'priority': 'medium',
                'recommendation': f'Standardize on 2-3 programming languages (currently using {summary["programming_languages"]})',
                'impact': 'Simplify hiring, training, and code maintenance'
            })
        
        # Risk recommendations
        if risk_assessment['high_risk_count'] > 0:
            recommendations.append({
                'category': 'Risk Management',
                'priority': 'high',
                'recommendation': f'Address {risk_assessment["high_risk_count"]} high-risk applications',
                'impact': 'Improve system reliability and reduce security exposure'
            })
        
        # Cloud migration
        if summary['cloud_ready_percentage'] < 50:
            recommendations.append({
                'category': 'Cloud Strategy',
                'priority': 'high',
                'recommendation': f'Only {summary["cloud_ready_percentage"]:.0f}% of applications are cloud-ready - plan modernization',
                'impact': 'Unlock cloud benefits: scalability, cost reduction, innovation'
            })
        
        # Data correlation
        if summary['correlation_status'] == 'not_started':
            recommendations.append({
                'category': 'Data Analysis',
                'priority': 'medium',
                'recommendation': 'Run correlation analysis to link infrastructure and code perspectives',
                'impact': 'Enable comprehensive rationalization and optimization planning'
            })
        
        return recommendations
    
    @staticmethod
    def get_dashboard_summary() -> Dict[str, Any]:
        """Quick summary for dashboard headers and cards"""
        corent_items = CorentData.query.all()
        cast_items = CASTData.query.all()
        app_inv_items = ApplicationInventory.query.all()
        
        return {
            'applications': len(set(
                list(i.app_id for i in corent_items) +
                list(i.app_id for i in cast_items)
            )),
            'capabilities': 5,  # Placeholder
            'duplicates': len(corent_items) - len(set(i.app_id for i in corent_items)),
            'maintenance_cost': InsightService._estimate_maintenance_cost(corent_items, app_inv_items),
            'scenarios': 3,  # Placeholder
            'correlation_complete': CorrelationResult.query.first() is not None,
            'data_quality_score': InsightService._calculate_data_quality_score(
                corent_items, cast_items, app_inv_items
            )
        }
