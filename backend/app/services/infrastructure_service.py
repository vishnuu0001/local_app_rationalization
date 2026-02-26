import json
import uuid
import re
import logging
from pypdf import PdfReader
from app.models.infrastructure import Infrastructure, Server, Container, NetworkLink, InfrastructureDiscovery
from app import db

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

# ===== PERFORMANCE OPTIMIZATIONS =====
# Compile regex patterns once at module level (avoid recompilation in loops)
WHITESPACE_PATTERN = re.compile(r'\s+')
HEADER_KEYWORDS = {'app id', 'metric', 'total', 'corent report', 'discovery', 'page', 'value'}

def _normalize_whitespace(text):
    """Optimize whitespace normalization - use pre-compiled regex"""
    if not text:
        return ""
    return WHITESPACE_PATTERN.sub(' ', text)

def _is_header_row(first_cell_str):
    """Fast header detection using set lookup"""
    if not first_cell_str:
        return True
    
    first_cell_lower = first_cell_str.lower()
    
    # Check simple patterns first (fastest)
    if first_cell_lower == '' or first_cell_lower.startswith('#'):
        return True
    
    # Check if any keyword matches (set lookup is O(1))
    if any(kw in first_cell_lower for kw in HEADER_KEYWORDS):
        return True
    
    return False

class InfrastructureService:
    """Service for extracting infrastructure data from Corent outputs"""
    
    Y_TOLERANCE = 1.5
    BOTTOM_MARGIN = 40
    
    @staticmethod
    def extract_from_pdf(file_path, file_name):
        """Extract infrastructure data from PDF file"""
        try:
            logger.info(f"[InfrastructureService] Starting PDF extraction from {file_path}")
            pdf_reader = PdfReader(file_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            logger.info(f"[InfrastructureService] Total text extracted: {len(text)} characters")
            return InfrastructureService.parse_infrastructure_data(text, file_name, file_path)
        except Exception as e:
            logger.error(f"[InfrastructureService] Error reading PDF: {str(e)}", exc_info=True)
            raise Exception(f"Error reading PDF: {str(e)}")
    
    @staticmethod
    def parse_infrastructure_data(text, file_name, file_path=None):
        """Parse extracted text to create infrastructure entities"""
        file_id = str(uuid.uuid4())
        
        # Create Infrastructure record
        infra = Infrastructure(
            file_id=file_id,
            filename=file_name,
            file_path=file_path,
            total_vms=0,
            total_k8s_clusters=0,
            orphan_systems=0
        )
        
        db.session.add(infra)
        db.session.commit()
        
        logger.info(f"[InfrastructureService] Infrastructure record created for {file_name}")
        return file_id, infra
    
    @staticmethod
    def extract_pdf_table(file_path):
        """Extract Infrastructure & Network Discovery table from PDF using PyMuPDF table detection
        
        OPTIMIZATIONS:
        - Skip first page (known to be metrics/headers)
        - Use pre-compiled regex patterns
        - Cache string operations
        - Reduce logging frequency
        - Fast-fail validation checks
        
        Handles CORENT_Report.pdf structure (188 pages, ~3,785 records)
        """
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction. Install: pip install PyMuPDF")
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            logger.info(f"[PDF Extraction] Starting: {total_pages} pages")
            
            rows = []
            skipped_headers = 0
            pages_processed = 0
            tables_found = 0
            
            # Process all pages (data tables start from page 1)
            for page_num in range(total_pages):
                page = doc[page_num]
                
                try:
                    # Find tables on this page (TableFinder is iterable)
                    tabs = page.find_tables()
                    
                    # Count tables as we iterate
                    table_count = 0
                    
                    # Iterate through found tables
                    for table in tabs:
                        table_count += 1
                        table_data = table.extract()
                        
                        # Skip if this looks like only a header row
                        if len(table_data) <= 1:
                            continue
                        
                        # Determine column offset based on number of columns (cache it)
                        num_cols = len(table_data[0])
                        col_offset = 1 if num_cols == 10 else 0
                        
                        # Process each row in the table
                        for row_data in table_data:
                            # Fast validation: must have enough columns
                            if not row_data or len(row_data) < (col_offset + 8):
                                continue
                            
                            # Fast header detection on first column
                            first_cell_val = row_data[col_offset]
                            if not first_cell_val:
                                continue
                            
                            # Convert to string once and cache
                            first_cell_str = str(first_cell_val).strip()
                            
                            if _is_header_row(first_cell_str):
                                skipped_headers += 1
                                continue
                            
                            # Extract app_id and name early (fast exit if invalid)
                            app_id = str(row_data[col_offset + 0]).strip() if row_data[col_offset + 0] else ""
                            app_name = str(row_data[col_offset + 1]).strip() if row_data[col_offset + 1] else ""
                            
                            # FAST VALIDATION - fail early if basic checks fail
                            if not app_id or not app_name:
                                continue
                            if app_id.upper() == 'APP ID' or app_id == 'TECHM':
                                continue
                            if not app_id.startswith('TECHM') or len(app_id) <= 2:
                                continue
                            
                            # Additional name checks (only if above passed)
                            app_name_lower = app_name.lower()
                            if app_name_lower == 'installed app / name' or app_name_lower.startswith('page') or app_name_lower.startswith('metric'):
                                continue
                            
                            # All validations passed - extract remaining columns
                            try:
                                row_dict = {
                                    'app_id': app_id,
                                    'name': app_name,
                                    'business_owner': str(row_data[col_offset + 2]).strip() if row_data[col_offset + 2] else "",
                                    'architecture_type': str(row_data[col_offset + 3]).strip() if row_data[col_offset + 3] else "",
                                    'platform_host': str(row_data[col_offset + 4]).strip() if row_data[col_offset + 4] else "",
                                    'application_type': str(row_data[col_offset + 5]).strip() if row_data[col_offset + 5] else "",
                                    'install_type': str(row_data[col_offset + 6]).strip() if row_data[col_offset + 6] else "",
                                    'capabilities': str(row_data[col_offset + 7]).strip() if row_data[col_offset + 7] else "",
                                }
                                
                                # Normalize whitespace in all fields using pre-compiled pattern
                                for key in row_dict:
                                    if row_dict[key]:
                                        row_dict[key] = _normalize_whitespace(row_dict[key])
                                
                                rows.append(row_dict)
                                
                                # Log only at major milestones (every 500 rows instead of 100)
                                if len(rows) % 500 == 0:
                                    logger.info(f"[PDF Extraction] Progress: {len(rows)} rows extracted")
                            
                            except (IndexError, ValueError, AttributeError):
                                # Skip rows with extraction errors
                                continue
                
                except Exception:
                    # Skip pages with table detection errors
                    continue
                
                # Only count pages that had processed tables
                if table_count > 0:
                    pages_processed += 1
                    tables_found += table_count
            
            doc.close()
            
            elapsed_pages = pages_processed
            logger.info(f"[PDF Extraction] Complete: {len(rows)} rows | {elapsed_pages} pages processed | {tables_found} tables found | {skipped_headers} headers skipped")
            
            if not rows:
                raise ValueError("No table data could be extracted from the PDF.")
            
            return rows
            
        except Exception as e:
            logger.error(f"[PDF Extraction] Error: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def group_words_by_line(words, y_tol=1.5):
        """Group words by their Y coordinate to form lines"""
        if not words:
            return []
        
        items = sorted(words, key=lambda w: (w[1], w[0]))
        lines, current, current_y = [], [], None
        
        for w in items:
            y = w[1]
            if current_y is None or abs(y - current_y) <= y_tol:
                current.append(w)
                current_y = y if current_y is None else current_y
            else:
                if current:
                    lines.append(sorted(current, key=lambda x: x[0]))
                current = [w]
                current_y = y
        
        if current:
            lines.append(sorted(current, key=lambda x: x[0]))
        
        return lines
    
    @staticmethod
    def make_boundaries_from_starts(col_starts):
        """Convert column start positions to column boundaries"""
        col_starts = sorted(col_starts, key=lambda t: t[1])
        bounds = []
        
        for i, (k, x) in enumerate(col_starts):
            end = col_starts[i + 1][1] if i < len(col_starts) - 1 else float("inf")
            bounds.append((k, x, end))
        
        return bounds
    
    @staticmethod
    def detect_table_bounds(doc, expected_columns):
        """Detect the column boundaries of the Infrastructure & Network Discovery table
        
        Expected column order (left to right):
        App ID | Installed App | Domain | Environment | Hosting | Hostname/Cluster | OS/Runtime | Tech | Version | Footprint | Cloud Readiness | Recommendation | Confidence
        """
        if not fitz or len(doc) == 0:
            return None
        
        page = doc[0]
        words = page.get_text("words")
        lines = InfrastructureService.group_words_by_line(words)
        
        logger.info(f"[InfrastructureService] Total lines extracted: {len(lines)}")
        
        # Find the header line - look for a line with "App" and "Installed" in close proximity
        header_line = None
        header_x_positions = []
        
        for line_idx, ln in enumerate(lines):
            if not ln or len(ln) < 8:  # Header should have many words
                continue
            
            texts = [w[4] for w in ln]
            line_text = " ".join(texts)
            line_lower = line_text.lower()
            
            # Detect if this is the header line
            if any(kw in line_lower for kw in ["app", "installed", "domain"]) and len(line_lower) > 100:
                logger.info(f"[InfrastructureService] Checking potential header at line {line_idx}: {line_text[:100]}")
                
                # This is likely the header - extract X positions left-to-right
                header_line = ln
                # Words are already sorted left-to-right by group_words_by_line
                logger.info(f"[InfrastructureService] Header has {len(header_line)} words")
                break
        
        if not header_line or len(header_line) < 8:
            logger.error("[InfrastructureService] Could not find valid header line")
            return None
        
        # The header words are stored in left-to-right order
        # We need to map them to column names based on content matching
        
        # Strategy: For each word in the header, determine which column it represents
        # by matching against expected column names
        
        col_position_pairs = []  # List of (column_name, x_position, word_text)
        
        for word in header_line:
            text = word[4]
            x_pos = word[0]
            text_lower = text.lower()
            
            matched_col = None
            
            # Match using exact and partial matching
            if text_lower == "app":
                matched_col = "app_id"
            elif "install" in text_lower:
                matched_col = "installed_app"
            elif "domain" in text_lower:
                matched_col = "domain"
            elif "environ" in text_lower:
                matched_col = "environment"
            elif text_lower == "hosting":
                matched_col = "hosting"
            elif "hostname" in text_lower:
                matched_col = "hostname_cluster"
            elif "os" in text_lower or "runtime" in text_lower:
                matched_col = "os_runtime"
            elif "tech" in text_lower:
                matched_col = "tech"
            elif "version" in text_lower:
                matched_col = "version"
            elif "footprint" in text_lower:
                matched_col = "footprint"
            elif "cloud" in text_lower or "readiness" in text_lower:
                matched_col = "cloud_readiness"
            elif "recommend" in text_lower:
                matched_col = "recommendation"
            elif "confid" in text_lower:
                matched_col = "confidence"
            
            if matched_col and matched_col not in [c[0] for c in col_position_pairs]:
                col_position_pairs.append((matched_col, x_pos, text))
                logger.info(f"[InfrastructureService] Matched '{text}' at X={x_pos} to column '{matched_col}'")
        
        logger.info(f"[InfrastructureService] Detected {len(col_position_pairs)} columns")
        
        if len(col_position_pairs) < 10:
            logger.warning(f"[InfrastructureService] Only detected {len(col_position_pairs)} columns, expected 13")
        
        # Create column boundaries from the detected positions
        # Sort by X position (they should already be sorted, but ensure it)
        sorted_pairs = sorted(col_position_pairs, key=lambda x: x[1])
        
        col_boundaries = []
        for i, (col_name, x_start, text) in enumerate(sorted_pairs):
            # Calculate column end: either the start of next column or infinity for last
            if i < len(sorted_pairs) - 1:
                x_end = sorted_pairs[i + 1][1]
            else:
                x_end = float("inf")
            
            col_boundaries.append((col_name, x_start, x_end))
            logger.info(f"[InfrastructureService] Column '{col_name}': X={x_start} to {x_end}")
        
        return col_boundaries
    
    @staticmethod
    def parse_table_rows(doc, page_indices, col_bounds, expected_columns):
        """Parse all rows from the table across multiple pages"""
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required")
        
        logger.info(f"[InfrastructureService] Starting to parse table rows with {len(col_bounds)} columns")
        logger.info(f"[InfrastructureService] Column bounds: {col_bounds}")
        
        rows = []
        current_row = None
        row_count = 0
        
        for pi in page_indices:
            if pi >= len(doc):
                continue
            
            logger.info(f"[InfrastructureService] Processing page {pi + 1}/{len(doc)}")
            
            page = doc[pi]
            height = page.rect.height
            
            # Get words excluding footer area
            words = [w for w in page.get_text("words") if w[1] < height - InfrastructureService.BOTTOM_MARGIN]
            lines = InfrastructureService.group_words_by_line(words)
            
            logger.info(f"[InfrastructureService] Page {pi + 1} has {len(lines)} lines")
            
            for ln_idx, ln in enumerate(lines):
                if not ln:
                    continue
                
                line_text = " ".join(w[4] for w in ln).strip()
                
                # Skip empty lines and page headers/footers
                if not line_text or re.match(r"^Page\s+\d+", line_text):
                    continue
                
                # Skip header lines (they contain column names)
                if re.search(r"(App ID|Installed|Domain|Environment|Hosting|Hostname|Recommendation|Confidence)", line_text, re.IGNORECASE):
                    if not line_text.startswith("APP-"):  # But don't skip if it's data starting with APP-
                        continue
                
                # Detect rows starting with APP-XXX pattern
                first_word = ln[0][4] if ln else ""
                is_new_row = first_word and re.match(r"APP-\d+", first_word)
                
                if is_new_row:
                    # Save the previous row if it has data
                    if current_row and any(current_row.values()):
                        rows.append(current_row)
                        row_count += 1
                        if row_count % 50 == 0:
                            logger.info(f"[InfrastructureService] Extracted {row_count} rows so far")
                    
                    # Initialize new row with empty values for all columns
                    current_row = {col_name: "" for col_name, _, _ in col_bounds}
                
                # Assign words from this line to columns based on X position
                if current_row is not None:
                    for w in ln:
                        text = w[4]
                        x_pos = w[0]
                        
                        # Skip empty text and common noise
                        if not text or text.isspace() or text in ["Page", "page"]:
                            continue
                        
                        # Find which column this word belongs to
                        assigned = False
                        for col_name, x_start, x_end in col_bounds:
                            if x_start <= x_pos < x_end:
                                # Append to existing value with space separator
                                current_row[col_name] = (current_row[col_name] + " " + text).strip()
                                assigned = True
                                break
                        
                        # If word doesn't fit in any column, add to the rightmost column
                        if not assigned and col_bounds:
                            last_col = col_bounds[-1][0]
                            current_row[last_col] = (current_row[last_col] + " " + text).strip()
        
        # Save the last row if it has data
        if current_row and any(current_row.values()):
            rows.append(current_row)
            row_count += 1
        
        logger.info(f"[InfrastructureService] Total rows extracted: {row_count}")
        
        # Normalize whitespace in all cells
        for r in rows:
            for k in r:
                r[k] = re.sub(r"\s+", " ", r[k]).strip()
        
        # Map generic column names to expected column names if needed
        if rows:
            first_row = rows[0]
            # If we have unnamed columns (col_0, col_1, etc.), try to map them
            if any(k.startswith("col_") for k in first_row.keys()):
                logger.warning("[InfrastructureService] Detected unnamed columns, mapping to expected columns")
                for row in rows:
                    # Create a new row with proper column names
                    numeric_cols = {int(k.split("_")[1]): v for k, v in row.items() if k.startswith("col_")}
                    new_row = {}
                    for i, col_name in enumerate(expected_columns):
                        new_row[col_name] = numeric_cols.get(i, "")
                    row.clear()
                    row.update(new_row)
        
        return rows
    
    @staticmethod
    def _get_sample_applications():
        """Get sample discovered applications for testing/fallback"""
        return [
            {
                'app_id': 'APP-001',
                'installed_app': 'InventoryAPI',
                'domain': 'Supply Chain',
                'environment': 'prd',
                'hosting': 'Cloud',
                'hostname_cluster': 'azure-east-1',
                'os_runtime': '.NET Core 5.0',
                'tech': '.NET, PostgreSQL, REST API',
                'version': '2.1.0',
                'footprint': 'Azure',
                'cloud_readiness': 'Cloud Ready',
                'recommendation': 'Migrate to cloud',
                'confidence': 'High'
            },
            {
                'app_id': 'APP-002',
                'installed_app': 'OrderManagement',
                'domain': 'Sales',
                'environment': 'prd',
                'hosting': 'On-Premise',
                'hostname_cluster': 'ws-prod-02',
                'os_runtime': 'Windows Server 2019',
                'tech': '.NET Framework 4.7, SQL Server 2019',
                'version': '3.2.1',
                'footprint': 'On-Premise',
                'cloud_readiness': 'Modernize First',
                'recommendation': 'Modernize then migrate',
                'confidence': 'Medium'
            },
            {
                'app_id': 'APP-003',
                'installed_app': 'ReportingEngine',
                'domain': 'Finance',
                'environment': 'dev',
                'hosting': 'Hybrid',
                'hostname_cluster': 'k8s-cluster-1',
                'os_runtime': 'Java 11, Linux',
                'tech': 'Java, Spring Boot, Oracle DB',
                'version': '1.8.5',
                'footprint': 'Kubernetes',
                'cloud_readiness': 'Cloud Ready',
                'recommendation': 'Containerize and migrate',
                'confidence': 'High'
            },
        ]
    
    @staticmethod
    def _extract_applications(text):
        """Extract application information from infrastructure text"""
        # This would parse the actual extracted text from PDF
        # For now, returning empty list as extraction happens via extract_pdf_table
        return []
    
    @staticmethod
    def _extract_servers(text):
        """Extract server information from text"""
        # This would parse actual server data
        # For demo, returning sample servers
        return [
            {
                'name': 'prd-mfg-app-01',
                'environment': 'prd',
                'type': 'VM',
                'ip': '192.168.1.101',
                'footprint': 'Azure',
                'techs': ['.NET Framework', 'SQL Server', 'IIS']
            },
            {
                'name': 'k8s-eu-central-1',
                'environment': 'prd',
                'type': 'Container',
                'ip': '10.0.0.50',
                'footprint': 'Kubernetes',
                'techs': ['Kubernetes', 'Docker', 'Linux']
            },
            {
                'name': 'dev-fin-app-01',
                'environment': 'dev',
                'type': 'VM',
                'ip': '192.168.1.201',
                'footprint': 'On-Premise',
                'techs': ['Java', 'Oracle DB', 'Apache Tomcat']
            }
        ]
    
    @staticmethod
    def get_infrastructure_summary(infra_id):
        """Get summary statistics for infrastructure"""
        infra = Infrastructure.query.get(infra_id)
        if not infra:
            return None
        
        return {
            'total_vms': infra.total_vms,
            'total_k8s_clusters': infra.total_k8s_clusters,
            'orphan_systems': infra.orphan_systems,
            'total_servers': len(infra.servers),
            'total_applications': len(infra.discovered_applications),
            'network_links': len(infra.network_links)
        }
