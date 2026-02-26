import json
import re
import datetime
import os
from typing import List, Dict, Any, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app import db
from app.models.pdf_report import PDFReport


class PDFExtractionService:
    """Service to extract structured data from PDF files and store as JSON"""
    
    # Tolerance for grouping words into lines (in points)
    Y_TOLERANCE = 1.5
    BOTTOM_MARGIN = 40
    
    @staticmethod
    def group_words_by_line(words: List[Tuple], y_tol: float = 1.5) -> List[List[Tuple]]:
        """
        Group words by their Y coordinate to form lines.
        
        Args:
            words: List of word tuples from PyMuPDF
            y_tol: Y-axis tolerance for grouping
            
        Returns:
            List of lines, where each line is a list of words
        """
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
    def make_boundaries_from_starts(col_starts: List[Tuple[str, float]]) -> List[Tuple[str, float, float]]:
        """
        Convert column start positions to column boundaries.
        
        Args:
            col_starts: List of (column_name, x_position) tuples
            
        Returns:
            List of (column_name, start_x, end_x) tuples
        """
        col_starts = sorted(col_starts, key=lambda t: t[1])
        bounds = []
        
        for i, (k, x) in enumerate(col_starts):
            end = col_starts[i + 1][1] if i < len(col_starts) - 1 else float("inf")
            bounds.append((k, x, end))
        
        return bounds
    
    @staticmethod
    def detect_main_table_bounds(doc) -> List[Tuple[str, float, float]]:
        """
        Detect the column boundaries of the main application discovery table.
        
        Args:
            doc: PyMuPDF document
            
        Returns:
            List of column boundaries
        """
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction")
        
        page = doc[0]
        words = page.get_text("words")
        lines = PDFExtractionService.group_words_by_line(words)
        
        # Find the header line containing column labels
        for ln in lines:
            texts = [w[4] for w in ln]
            
            if all(col in texts for col in ["App", "ID", "Installed", "Domain"]):
                starts = {}
                
                for w in ln:
                    t, x = w[4], w[0]
                    
                    # Match column headers
                    if t == "App" and x < 60:
                        starts["app_id"] = x
                    elif t == "Installed":
                        starts["installed_app"] = x
                    elif t == "Domain":
                        starts["domain"] = x
                    elif t == "Environ":
                        starts["environment"] = x
                    elif t == "Hosting":
                        starts["hosting"] = x
                    elif t == "Hostname/Cluster":
                        starts["hostname_cluster"] = x
                    elif t == "OS/Runtime":
                        starts["os_runtime"] = x
                    elif t == "Tech":
                        starts["tech"] = x
                    elif t == "Version":
                        starts["version"] = x
                    elif t == "Footprint":
                        starts["footprint"] = x
                    elif t == "Cloud":
                        starts["cloud_readiness"] = x
                    elif t == "Recommenda":
                        starts["recommendation"] = x
                    elif t == "Confiden":
                        starts["confidence"] = x
                
                required = [
                    "app_id", "installed_app", "domain", "environment", "hosting",
                    "hostname_cluster", "os_runtime", "tech", "version", "footprint",
                    "cloud_readiness", "recommendation", "confidence"
                ]
                
                if all(k in starts for k in required):
                    return PDFExtractionService.make_boundaries_from_starts(
                        [(k, starts[k]) for k in required]
                    )
        
        raise ValueError("Could not detect main table columns")
    
    @staticmethod
    def parse_table(
        doc,
        page_indices: List[int],
        col_bounds: List[Tuple[str, float, float]],
        start_regex: str = r"APP-\d{3}",
        bottom_margin: int = 40
    ) -> List[Dict[str, str]]:
        """
        Parse a table from PDF pages.
        
        Args:
            doc: PyMuPDF document
            page_indices: List of page indices to parse
            col_bounds: Column boundaries
            start_regex: Regex pattern for row start markers
            bottom_margin: Pixels from bottom to ignore (footer area)
            
        Returns:
            List of row dictionaries
        """
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction")
        
        start_pat = re.compile(r"^" + start_regex + r"$")
        rows, current = [], None
        
        for pi in page_indices:
            if pi >= len(doc):
                continue
            
            page = doc[pi]
            height = page.rect.height
            
            # Get words excluding footer area
            words = [w for w in page.get_text("words") if w[1] < height - bottom_margin]
            lines = PDFExtractionService.group_words_by_line(words)
            
            for ln in lines:
                if not ln:
                    continue
                
                line_text = " ".join(w[4] for w in ln).strip()
                
                # Skip page number lines
                if re.fullmatch(r"Page\s+\d+", line_text):
                    continue
                
                # Check if this is a new row
                left_word = min(ln, key=lambda w: w[0])
                is_new_row = (
                    left_word[4].startswith("APP-")
                    and start_pat.match(left_word[4])
                    and col_bounds[0][1] - 1 <= left_word[0] < col_bounds[0][2] + 1
                )
                
                if is_new_row:
                    if current:
                        rows.append(current)
                    current = {k: "" for k, _, _ in col_bounds}
                
                if current:
                    for w in ln:
                        t, x = w[4], w[0]
                        if t == "Page":
                            continue
                        
                        # Assign word to appropriate column
                        for k, start, end in col_bounds:
                            if start <= x < end:
                                current[k] = (current[k] + " " + t).strip()
                                break
        
        if current:
            rows.append(current)
        
        # Normalize whitespace in all cells
        for r in rows:
            for k in r:
                r[k] = re.sub(r"\s+", " ", r[k]).strip()
        
        return rows
    
    @staticmethod
    def detect_exceptions_table_bounds(doc) -> Optional[List[Tuple[str, float, float]]]:
        """
        Detect the column boundaries of the exceptions table (usually on last page).
        
        Args:
            doc: PyMuPDF document
            
        Returns:
            List of column boundaries or None if not found
        """
        if not fitz or len(doc) == 0:
            return None
        
        last = doc[len(doc) - 1]
        w = last.get_text("words")
        lines = PDFExtractionService.group_words_by_line(w)
        
        for ln in lines:
            texts = [x[4] for x in ln]
            
            if all(col in texts for col in ["App", "ID", "Installed", "Environment", "Notes"]):
                tmp = {}
                
                for word in ln:
                    t, x = word[4], word[0]
                    
                    if t == "App" and x < 70:
                        tmp["app_id"] = x
                    elif t == "Installed":
                        tmp["installed_app"] = x
                    elif t == "Environment":
                        tmp["environment"] = x
                    elif t == "Hostname/Cluster":
                        tmp["hostname_cluster"] = x
                    elif t == "Notes":
                        tmp["notes"] = x
                    elif t == "Recommendation":
                        tmp["recommendation"] = x
                
                if len(tmp) >= 5:  # At minimum need most columns
                    return PDFExtractionService.make_boundaries_from_starts(
                        [(k, tmp[k]) for k in ["app_id", "installed_app", "environment", "hostname_cluster", "notes", "recommendation"] if k in tmp]
                    )
        
        return None
    
    @staticmethod
    def extract_report_metadata(text: str) -> Dict[str, Optional[str]]:
        """
        Extract metadata (company, report date) from first page text.
        
        Args:
            text: Raw text from first page
            
        Returns:
            Dict with company and report_date
        """
        metadata = {
            "company": None,
            "report_date": None,
        }
        
        m = re.search(
            r"Company:\s*(.+?)\s*\|\s*Report Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
            text
        )
        if m:
            metadata["company"] = m.group(1).strip()
            metadata["report_date"] = m.group(2).strip()
        
        return metadata
    
    @classmethod
    def extract_from_pdf(cls, pdf_path: str, report_type: str = "infrastructure") -> Dict[str, Any]:
        """
        Extract structured data from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            report_type: Type of report ('infrastructure' or 'code_analysis')
            
        Returns:
            Dictionary containing extracted data
            
        Raises:
            ImportError: If PyMuPDF is not installed
            ValueError: If PDF parsing fails
            FileNotFoundError: If PDF file not found
        """
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            
            # Extract raw text from all pages
            raw_pages = [doc[i].get_text() for i in range(len(doc))]
            
            # Extract metadata
            metadata = cls.extract_report_metadata(raw_pages[0] if raw_pages else "")
            
            # Extract main table
            try:
                main_bounds = cls.detect_main_table_bounds(doc)
                main_rows = cls.parse_table(
                    doc, 
                    page_indices=list(range(0, min(7, len(doc)))), 
                    col_bounds=main_bounds
                )
            except (ValueError, IndexError) as e:
                main_rows = []
                main_bounds = []
                print(f"Warning: Could not extract main table: {str(e)}")
            
            # Extract exceptions table
            try:
                exc_bounds = cls.detect_exceptions_table_bounds(doc)
                if exc_bounds:
                    exc_rows = cls.parse_table(
                        doc,
                        page_indices=[len(doc) - 1],
                        col_bounds=exc_bounds
                    )
                else:
                    exc_rows = []
            except (ValueError, IndexError) as e:
                exc_rows = []
                exc_bounds = []
                print(f"Warning: Could not extract exceptions table: {str(e)}")
            
            doc.close()
            
            # Build result payload
            result = {
                "source_pdf": pdf_path,
                "extracted_at": datetime.datetime.utcnow().isoformat() + "Z",
                "report_type": report_type,
                "report_metadata": metadata,
                "sections": {
                    "application_discovery_summary": {
                        "row_count": len(main_rows),
                        "columns": [k for k, _, _ in main_bounds] if main_bounds else [],
                        "rows": main_rows
                    },
                    "exceptions_gaps_discovery_notes": {
                        "row_count": len(exc_rows),
                        "columns": [k for k, _, _ in exc_bounds] if exc_bounds else [],
                        "rows": exc_rows
                    }
                },
                "raw_text_pages": raw_pages
            }
            
            return result
            
        except Exception as e:
            raise ValueError(f"Error extracting PDF: {str(e)}")
    
    @classmethod
    def extract_and_store(cls, pdf_path: str, report_type: str = "infrastructure") -> PDFReport:
        """
        Extract PDF data and store it in the database.
        
        Args:
            pdf_path: Path to PDF file
            report_type: Type of report ('infrastructure' or 'code_analysis')
            
        Returns:
            PDFReport database object
            
        Raises:
            ImportError: If PyMuPDF is not installed
            ValueError: If PDF parsing fails
        """
        # Extract data from PDF
        extracted_data = cls.extract_from_pdf(pdf_path, report_type)
        
        # Store in database
        pdf_report = PDFReport(
            source_pdf=pdf_path,
            payload=extracted_data,
            report_type=report_type,
            extracted_at=datetime.datetime.utcnow()
        )
        
        db.session.add(pdf_report)
        db.session.commit()
        
        return pdf_report
    
    @classmethod
    def get_report(cls, report_id: int) -> Optional[PDFReport]:
        """Get a PDF report by ID"""
        return PDFReport.query.get(report_id)
    
    @classmethod
    def get_reports_by_type(cls, report_type: str) -> List[PDFReport]:
        """Get all reports of a specific type"""
        return PDFReport.query.filter_by(report_type=report_type).all()
    
    @classmethod
    def search_in_reports(cls, query: str, report_type: Optional[str] = None):
        """
        Search for content in extracted reports.
        
        Args:
            query: Search term
            report_type: Optional filter by report type
            
        Returns:
            List of matching PDFReport objects
        """
        q = PDFReport.query
        
        if report_type:
            q = q.filter_by(report_type=report_type)
        
        # Search in the JSON payload
        # Note: This is a basic search. For production, use PostgreSQL full-text search
        results = []
        for report in q.all():
            if cls._search_in_payload(report.payload, query):
                results.append(report)
        
        return results
    
    @staticmethod
    def _search_in_payload(payload: Dict, query: str) -> bool:
        """Search for a string in the payload"""
        query_lower = query.lower()
        payload_str = json.dumps(payload).lower()
        return query_lower in payload_str
