"""CAST Analysis PDF Extraction Service"""

import logging
import re
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

# ===== PERFORMANCE OPTIMIZATIONS =====
# Pre-compiled regex patterns
WHITESPACE_PATTERN = re.compile(r'\s+')
HEADER_KEYWORDS = {'app id', 'application', 'metric', 'total', 'report', 'page', 'value'}

def _normalize_whitespace(text):
    """Optimize whitespace normalization"""
    if not text:
        return ""
    return WHITESPACE_PATTERN.sub(' ', text)

def _is_header_row(first_cell_str, second_cell_str=None):
    """
    Fast header detection - checks both first and second cell
    For 13-column tables with empty first column, check second cell instead
    """
    # If first cell is empty, check second cell
    if not first_cell_str or str(first_cell_str).strip() == "":
        if second_cell_str:
            first_cell_str = second_cell_str
        else:
            return True
    
    first_cell_lower = str(first_cell_str).lower().strip()
    
    # Empty cell or starts with # = header
    if first_cell_lower == '' or first_cell_lower.startswith('#'):
        return True
    
    # Check for common header keywords
    if any(kw in first_cell_lower for kw in HEADER_KEYWORDS):
        return True
    
    # "Rank", "Risk", numeric IDs = not header
    if first_cell_lower in ['rank', 'risk', 'total', 'page']:
        return False
    
    return False


class CASTAnalysisService:
    """Service for extracting CAST Analysis data from PDF"""
    
    @staticmethod
    def extract_pdf_tables(file_path):
        """
        Extract CAST Analysis tables from PDF
        Expected tables:
        1. Application Inventory (12 or 13 columns)
        2. Application Classification (6 or 7 columns)
        3. Internal Architecture (9 or 10 columns with empty first or varied format)
        4. High-Risk Applications (10 columns with Rank first)
        """
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction. Install: pip install PyMuPDF")
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            logger.info(f"[CAST Extraction] Starting: {total_pages} pages")
            
            app_inventory_rows = []
            app_classification_rows = []
            internal_architecture_rows = []
            high_risk_applications_rows = []
            
            pages_processed = 0
            tables_found = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                try:
                    tabs = page.find_tables()
                    
                    table_count = 0
                    for table in tabs:
                        table_count += 1
                        table_data = table.extract()
                        
                        if len(table_data) <= 1:
                            continue
                        
                        # Determine which table type by column count and structure
                        num_cols = len(table_data[0])
                        first_cell = str(table_data[0][0]).strip() if table_data[0][0] else ""
                        
                        # Extract based on column count and first cell
                        # Inventory: 12 or 13 columns
                        if num_cols in (12, 13):
                            _extract_app_inventory(table_data, app_inventory_rows)
                        # Classification: 6 or 7 columns
                        elif num_cols in (6, 7):
                            _extract_app_classification(table_data, app_classification_rows)
                        # Architecture: 10 columns
                        elif num_cols == 10:
                            # Check if it's high-risk (Rank-based) or regular architecture
                            if first_cell.lower() == "rank":
                                _extract_high_risk_applications(table_data, high_risk_applications_rows)
                            else:
                                _extract_internal_architecture(table_data, internal_architecture_rows)
                        # Architecture: 9, 11, or other columns
                        elif num_cols in (9, 11):
                            _extract_internal_architecture(table_data, internal_architecture_rows)
                    
                    if table_count > 0:
                        pages_processed += 1
                        tables_found += table_count
                
                except Exception:
                    continue
            
            doc.close()
            
            logger.info(f"[CAST Extraction] Complete: App Inventory={len(app_inventory_rows)}, Classification={len(app_classification_rows)}, Architecture={len(internal_architecture_rows)}, High-Risk={len(high_risk_applications_rows)}")
            
            return {
                'app_inventory': app_inventory_rows,
                'app_classification': app_classification_rows,
                'internal_architecture': internal_architecture_rows,
                'high_risk_applications': high_risk_applications_rows,
                'pages_processed': pages_processed,
                'tables_found': tables_found,
            }
            
        except Exception as e:
            logger.error(f"[CAST Extraction] Error: {str(e)}", exc_info=True)
            raise


def _extract_app_inventory(table_data, rows):
    """Extract Application Inventory table (12 or 13 columns)"""
    num_cols = len(table_data[0]) if table_data else 0
    
    # Determine if we have 13-col (with empty first col) or 12-col format
    has_empty_first_col = (num_cols == 13)
    start_col = 1 if has_empty_first_col else 0
    
    for row_data in table_data:
        if not row_data or len(row_data) < (12 + start_col):
            continue
        
        # Check for header row - use second cell if first is empty
        first_cell = str(row_data[start_col]).strip() if row_data[start_col] else ""
        if _is_header_row(first_cell, str(row_data[start_col] if start_col > 0 else None)):
            continue
        
        # Extract columns starting from appropriate offset
        try:
            app_id = str(row_data[start_col + 0]).strip() if row_data[start_col + 0] else ""
            application = str(row_data[start_col + 1]).strip() if row_data[start_col + 1] else ""
            
            # Fast validation
            if not app_id or not application:
                continue
            
            if app_id.upper() == 'APP ID' or application.upper() == 'APPLICATION':
                continue
            
            row_dict = {
                'app_id': app_id,
                'application': application,
                'repo': str(row_data[start_col + 2]).strip() if row_data[start_col + 2] else "",
                'primary_language': str(row_data[start_col + 3]).strip() if row_data[start_col + 3] else "",
                'framework': str(row_data[start_col + 4]).strip() if row_data[start_col + 4] else "",
                'loc_k': _to_float(row_data[start_col + 5]),
                'modules': _to_int(row_data[start_col + 6]),
                'db_name': str(row_data[start_col + 7]).strip() if row_data[start_col + 7] else "",
                'ext_int': str(row_data[start_col + 8]).strip() if row_data[start_col + 8] else "",
                'quality': str(row_data[start_col + 9]).strip() if row_data[start_col + 9] else "",
                'security': str(row_data[start_col + 10]).strip() if row_data[start_col + 10] else "",
                'cloud_ready': str(row_data[start_col + 11]).strip() if row_data[start_col + 11] else "",
            }
            
            # Normalize whitespace
            for key in row_dict:
                if isinstance(row_dict[key], str):
                    row_dict[key] = _normalize_whitespace(row_dict[key])
            
            rows.append(row_dict)
            
            if len(rows) % 100 == 0:
                logger.info(f"[CAST] App Inventory: {len(rows)} rows extracted")
        
        except Exception:
            continue


def _extract_app_classification(table_data, rows):
    """Extract Application Classification table (6 or 7 columns)"""
    num_cols = len(table_data[0]) if table_data else 0
    
    # Determine if we have 7-col (with empty first col) or 6-col format
    has_empty_first_col = (num_cols == 7)
    start_col = 1 if has_empty_first_col else 0
    
    for row_data in table_data:
        if not row_data or len(row_data) < (6 + start_col):
            continue
        
        # Check for header row
        first_cell = str(row_data[start_col]).strip() if row_data[start_col] else ""
        if _is_header_row(first_cell, str(row_data[start_col] if start_col > 0 else None)):
            continue
        
        # Extract columns
        try:
            app_id = str(row_data[start_col + 0]).strip() if row_data[start_col + 0] else ""
            application = str(row_data[start_col + 1]).strip() if row_data[start_col + 1] else ""
            
            # Fast validation
            if not app_id or not application:
                continue
            
            if app_id.upper() == 'APP ID' or application.upper() == 'APPLICATION':
                continue
            
            row_dict = {
                'app_id': app_id,
                'application': application,
                'business_owner': str(row_data[start_col + 2]).strip() if row_data[start_col + 2] else "",
                'application_type': str(row_data[start_col + 3]).strip() if row_data[start_col + 3] else "",
                'install_type': str(row_data[start_col + 4]).strip() if row_data[start_col + 4] else "",
                'capabilities': str(row_data[start_col + 5]).strip() if row_data[start_col + 5] else "",
            }
            
            # Normalize whitespace
            for key in row_dict:
                if isinstance(row_dict[key], str):
                    row_dict[key] = _normalize_whitespace(row_dict[key])
            
            rows.append(row_dict)
            
            if len(rows) % 100 == 0:
                logger.info(f"[CAST] App Classification: {len(rows)} rows extracted")
        
        except Exception:
            continue


def _extract_internal_architecture(table_data, rows):
    """Extract Internal Architecture table (9 or 10 columns)"""
    num_cols = len(table_data[0]) if table_data else 0
    
    # Determine if we have 10-col (with rank first col) or 9-col format
    # 10-col format: Rank, APP ID, Application, Risk, Quality, Security, Cloud, App Type, Install Type, Capabilities
    # 9-col format: APP ID, Application, Module, Layer, Language, DB Calls, External Calls, App Type, Install Type
    has_rank_col = (num_cols == 10)
    start_col = 1 if has_rank_col else 0
    
    for row_data in table_data:
        if not row_data or len(row_data) < (9 + (1 if has_rank_col else 0)):
            continue
        
        # Check for header row (check both first and second cell for 10-col tables)
        check_cell = str(row_data[start_col]).strip() if row_data[start_col] else ""
        if _is_header_row(check_cell, str(row_data[start_col] if start_col > 0 else None)):
            continue
        
        # Extract columns
        try:
            # For 10-col tables: skip rank, extract from App ID onwards
            # For 9-col tables: extract from col 0 onwards
            app_id = str(row_data[start_col + 0]).strip() if row_data[start_col + 0] else ""
            application = str(row_data[start_col + 1]).strip() if row_data[start_col + 1] else ""
            
            # Fast validation
            if not app_id or not application:
                continue
            
            if app_id.upper() == 'APP ID' or application.upper() == 'APPLICATION':
                continue
            
            # Extract based on format
            if has_rank_col:
                # 10-col format from PDF: cols are Risk, Quality, Security, Cloud, App Type, Install Type, Capabilities
                row_dict = {
                    'app_id': app_id,
                    'application': application,
                    'module': str(row_data[start_col + 2]).strip() if row_data[start_col + 2] else "",  # Risk
                    'layer': str(row_data[start_col + 3]).strip() if row_data[start_col + 3] else "",   # Quality
                    'language': str(row_data[start_col + 4]).strip() if row_data[start_col + 4] else "",  # Security
                    'db_calls': _to_int(row_data[start_col + 5]),  # Cloud rating
                    'external_calls': _to_int(0),  # Not available in 10-col format
                    'app_type': str(row_data[start_col + 6]).strip() if row_data[start_col + 6] else "",
                    'install_type': str(row_data[start_col + 7]).strip() if row_data[start_col + 7] else "",
                }
            else:
                # 9-col format (standard)
                row_dict = {
                    'app_id': app_id,
                    'application': application,
                    'module': str(row_data[start_col + 2]).strip() if row_data[start_col + 2] else "",
                    'layer': str(row_data[start_col + 3]).strip() if row_data[start_col + 3] else "",
                    'language': str(row_data[start_col + 4]).strip() if row_data[start_col + 4] else "",
                    'db_calls': _to_int(row_data[start_col + 5]),
                    'external_calls': _to_int(row_data[start_col + 6]),
                    'app_type': str(row_data[start_col + 7]).strip() if row_data[start_col + 7] else "",
                    'install_type': str(row_data[start_col + 8]).strip() if row_data[start_col + 8] else "",
                }
            
            # Normalize whitespace
            for key in row_dict:
                if isinstance(row_dict[key], str):
                    row_dict[key] = _normalize_whitespace(row_dict[key])
            
            rows.append(row_dict)
            
            if len(rows) % 100 == 0:
                logger.info(f"[CAST] Internal Architecture: {len(rows)} rows extracted")
        
        except Exception:
            continue


def _to_int(value):
    """Convert value to integer safely"""
    if not value:
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError, AttributeError):
        return None


def _extract_high_risk_applications(table_data, rows):
    """Extract High-Risk Applications table (10 columns with Rank first)"""
    # Format: Rank, APP ID, Application, Risk, Quality, Security, Cloud, App Type, Install Type, Capabilities
    
    for row_data in table_data:
        if not row_data or len(row_data) < 10:
            continue
        
        # Check for header row
        first_cell = str(row_data[0]).strip() if row_data[0] else ""
        if first_cell.lower() == "rank" or _is_header_row(first_cell):
            continue
        
        try:
            rank = _to_int(row_data[0])
            app_id = str(row_data[1]).strip() if row_data[1] else ""
            application = str(row_data[2]).strip() if row_data[2] else ""
            
            # Fast validation
            if not app_id or not application:
                continue
            
            if app_id.upper() == 'APP ID' or application.upper() == 'APPLICATION':
                continue
            
            row_dict = {
                'rank': rank,
                'app_id': app_id,
                'application': application,
                'risk': str(row_data[3]).strip() if row_data[3] else "",
                'quality': str(row_data[4]).strip() if row_data[4] else "",
                'security': str(row_data[5]).strip() if row_data[5] else "",
                'cloud': str(row_data[6]).strip() if row_data[6] else "",
                'app_type': str(row_data[7]).strip() if row_data[7] else "",
                'install_type': str(row_data[8]).strip() if row_data[8] else "",
                'capabilities': str(row_data[9]).strip() if row_data[9] else "",
            }
            
            # Normalize whitespace
            for key in row_dict:
                if isinstance(row_dict[key], str):
                    row_dict[key] = _normalize_whitespace(row_dict[key])
            
            rows.append(row_dict)
            
            if len(rows) % 100 == 0:
                logger.info(f"[CAST] High-Risk Applications: {len(rows)} rows extracted")
        
        except Exception:
            continue


def _to_float(value):
    """Convert value to float safely"""
    if not value:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None
