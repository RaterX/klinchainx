import os
import sys
import time
import logging
import argparse
import traceback
from typing import List, Dict, Any, Optional, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tempfile
import shutil
import re
import PyPDF2
import pandas as pd
import numpy as np
from tqdm import tqdm
import chardet
import fitz  # PyMuPDF - alternative PDF reader for better text extraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_processing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("pdf_processor")


class PDFProcessor:
    """Production-ready PDF processing class with robust error handling and optimization."""
    
    def __init__(self, 
                 output_format: str = 'csv', 
                 chunk_size: int = 1000, 
                 max_workers: int = 4,
                 extraction_method: str = 'auto',
                 include_metadata: bool = True):
        """
        Initialize the PDF processor with configuration options.
        
        Args:
            output_format: Format to save results ('csv', 'json', 'parquet')
            chunk_size: Maximum lines to process in memory at once
            max_workers: Maximum number of parallel workers for multi-file processing
            extraction_method: Text extraction method ('pypdf', 'pymupdf', 'auto')
            include_metadata: Whether to include PDF metadata in output
        """
        self.output_format = output_format.lower()
        self.chunk_size = chunk_size
        self.max_workers = max_workers
        self.extraction_method = extraction_method
        self.include_metadata = include_metadata
        
        logger.info(f"Initialized PDFProcessor with: output_format={output_format}, "
                    f"chunk_size={chunk_size}, max_workers={max_workers}, "
                    f"extraction_method={extraction_method}")
        
    def process_file(self, pdf_file: Union[str, Path], output_file: Optional[str] = None) -> str:
        """
        Process a single PDF file and save the extracted text to the specified output file.
        
        Args:
            pdf_file: Path to the PDF file to process
            output_file: Path to the output file (if None, auto-generated)
            
        Returns:
            Path to the created output file
        """
        start_time = time.time()
        pdf_path = Path(pdf_file)
        
        # Validate input file
        if not self._validate_input_file(pdf_path):
            return ""
        
        # Generate output filename if not provided
        if not output_file:
            output_file = f"{pdf_path.stem}_extracted.{self.output_format}"
        
        try:
            logger.info(f"Processing PDF: {pdf_file}")
            
            # Extract text from PDF
            text_data = self._extract_text_from_pdf(pdf_path)
            
            # Save extracted text
            saved_path = self._save_text_data(text_data, output_file)
            
            processing_time = time.time() - start_time
            logger.info(f"Successfully processed {pdf_file} in {processing_time:.2f} seconds. "
                      f"Output saved to {saved_path}")
            
            return saved_path
            
        except Exception as e:
            logger.error(f"Error processing {pdf_file}: {str(e)}")
            logger.debug(traceback.format_exc())
            return ""
    
    def process_directory(self, input_dir: Union[str, Path], output_dir: Optional[Union[str, Path]] = None, 
                         pattern: str = "*.pdf") -> List[str]:
        """
        Process all PDF files in the specified directory.
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory to save output files (creates if doesn't exist)
            pattern: Glob pattern to match PDF files
            
        Returns:
            List of paths to output files
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            logger.error(f"Input directory does not exist: {input_dir}")
            return []
        
        # Setup output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)
        else:
            output_path = input_path / "extracted_text"
            output_path.mkdir(exist_ok=True, parents=True)
        
        # Find all PDF files
        pdf_files = list(input_path.glob(pattern))
        if not pdf_files:
            logger.warning(f"No PDF files found in {input_dir} matching pattern '{pattern}'")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        results = []
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and track with progress bar
            future_to_file = {
                executor.submit(self.process_file, 
                               pdf_file, 
                               output_path / f"{pdf_file.stem}.{self.output_format}"): pdf_file
                for pdf_file in pdf_files
            }
            
            # Show progress with tqdm
            with tqdm(total=len(pdf_files), desc="Processing PDFs") as pbar:
                for future in as_completed(future_to_file):
                    pdf_file = future_to_file[future]
                    try:
                        output_file = future.result()
                        if output_file:
                            results.append(output_file)
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"Error processing {pdf_file}: {str(e)}")
        
        logger.info(f"Completed processing {len(results)} files successfully out of {len(pdf_files)} total files")
        return results
        
    def _validate_input_file(self, file_path: Path) -> bool:
        """Validate that the input file exists and is a valid PDF."""
        # Check if file exists
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False
        
        # Check file extension
        if file_path.suffix.lower() != '.pdf':
            logger.error(f"File is not a PDF: {file_path}")
            return False
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 500:  # Warning for very large files
            logger.warning(f"Large PDF detected ({file_size_mb:.2f} MB): {file_path}. Processing may take time.")
        
        # Basic PDF validation
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    logger.error(f"File is not a valid PDF (invalid header): {file_path}")
                    return False
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False
            
        return True
            
    def _extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract text and metadata from a PDF file using the specified method.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        method = self.extraction_method.lower()
        
        try:
            # First, try to extract metadata regardless of method
            metadata = self._extract_metadata(pdf_path) if self.include_metadata else {}
            
            if method == 'auto':
                # Try PyMuPDF first, fallback to PyPDF2
                try:
                    text_lines = self._extract_with_pymupdf(pdf_path)
                except Exception as e:
                    logger.warning(f"PyMuPDF extraction failed, falling back to PyPDF2: {str(e)}")
                    text_lines = self._extract_with_pypdf(pdf_path)
            elif method == 'pymupdf':
                text_lines = self._extract_with_pymupdf(pdf_path)
            else:  # default to pypdf
                text_lines = self._extract_with_pypdf(pdf_path)
                
            # Create result with page separation
            return {
                'text': text_lines,
                'metadata': metadata,
                'filename': pdf_path.name,
                'extraction_method': method,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
                
        except MemoryError:
            logger.error(f"Memory error while processing {pdf_path}. File may be too large.")
            # Try to process in smaller chunks if it's a memory error
            return self._extract_text_in_chunks(pdf_path)
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            logger.debug(traceback.format_exc())
            return {'text': [], 'metadata': {}, 'error': str(e)}
    
    def _extract_with_pypdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text using PyPDF2."""
        try:
            pdf_reader = PyPDF2.PdfReader(str(pdf_path))
            total_pages = len(pdf_reader.pages)
            text_lines = []
            
            # Extract text from each page with progress reporting for large documents
            for page_num in tqdm(range(total_pages), desc="Extracting pages", disable=total_pages < 10):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text() or ""
                    
                    # Clean and split the text
                    lines = text.split('\n')
                    clean_lines = []
                    for line in lines:
                        line = self._clean_text(line)
                        if line:
                            clean_lines.append(line)
                    
                    # Store page info with the text
                    text_lines.append({
                        'page': page_num + 1,
                        'content': clean_lines,
                        'page_size': len(text)
                    })
                    
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    text_lines.append({
                        'page': page_num + 1,
                        'content': [],
                        'error': str(e)
                    })
            
            return text_lines
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {str(e)}")
            raise
            
    def _extract_with_pymupdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text using PyMuPDF (often better quality than PyPDF2)."""
        try:
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            text_lines = []
            
            for page_num in tqdm(range(total_pages), desc="Extracting pages", disable=total_pages < 10):
                try:
                    page = doc[page_num]
                    text = page.get_text() or ""
                    
                    # Clean and split the text
                    lines = text.split('\n')
                    clean_lines = []
                    for line in lines:
                        line = self._clean_text(line)
                        if line:
                            clean_lines.append(line)
                    
                    # Store page info with the text
                    text_lines.append({
                        'page': page_num + 1,
                        'content': clean_lines,
                        'page_size': len(text)
                    })
                    
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    text_lines.append({
                        'page': page_num + 1,
                        'content': [],
                        'error': str(e)
                    })
            
            doc.close()
            return text_lines
        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {str(e)}")
            raise
    
    def _extract_text_in_chunks(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract text from a large PDF in chunks to avoid memory issues.
        Uses temporary files for each chunk.
        """
        logger.info(f"Processing large PDF in chunks: {pdf_path}")
        
        # Create a temporary directory for chunk processing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Try to split the PDF into smaller chunks using PyMuPDF
                doc = fitz.open(str(pdf_path))
                total_pages = len(doc)
                chunk_size = min(20, max(1, total_pages // 10))  # Calculate chunk size
                text_lines = []
                
                for start_page in range(0, total_pages, chunk_size):
                    end_page = min(start_page + chunk_size - 1, total_pages - 1)
                    logger.debug(f"Processing pages {start_page} to {end_page}")
                    
                    # Extract text from page range
                    chunk_text = []
                    for page_num in range(start_page, end_page + 1):
                        try:
                            page = doc[page_num]
                            text = page.get_text() or ""
                            lines = text.split('\n')
                            clean_lines = []
                            for line in lines:
                                line = self._clean_text(line)
                                if line:
                                    clean_lines.append(line)
                            
                            chunk_text.append({
                                'page': page_num + 1,
                                'content': clean_lines,
                                'page_size': len(text)
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error in chunk processing, page {page_num}: {str(e)}")
                            chunk_text.append({
                                'page': page_num + 1,
                                'content': [],
                                'error': str(e)
                            })
                    
                    text_lines.extend(chunk_text)
                    
                doc.close()
                
                metadata = self._extract_metadata(pdf_path) if self.include_metadata else {}
                return {
                    'text': text_lines,
                    'metadata': metadata,
                    'filename': pdf_path.name,
                    'extraction_method': 'chunked',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
            except Exception as e:
                logger.error(f"Chunk processing failed: {str(e)}")
                return {
                    'text': [],
                    'metadata': {},
                    'filename': pdf_path.name,
                    'error': f"Chunk processing failed: {str(e)}",
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
    
    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract metadata from PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                info = reader.metadata
                if info:
                    # Convert to regular dictionary and handle XMP metadata
                    metadata = {
                        'title': info.get('/Title', ''),
                        'author': info.get('/Author', ''),
                        'creator': info.get('/Creator', ''),
                        'producer': info.get('/Producer', ''),
                        'subject': info.get('/Subject', ''),
                        'creation_date': info.get('/CreationDate', ''),
                        'modification_date': info.get('/ModDate', ''),
                        'pages': len(reader.pages)
                    }
                    return {k: str(v) for k, v in metadata.items()}
                return {'pages': len(reader.pages)}
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")
            return {}
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing excess whitespace and invalid characters.
        
        Args:
            text: Text string to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
            
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
                
    def _save_text_data(self, text_data: Dict[str, Any], output_file: str) -> str:
        """
        Save extracted text data to the specified output format.
        
        Args:
            text_data: Dictionary containing extracted text and metadata
            output_file: Path to output file
            
        Returns:
            Path to saved file
        """
        try:
            # Flatten the data structure for tabular formats
            flattened_data = []
            
            # Extract common metadata
            common_metadata = {
                'filename': text_data.get('filename', ''),
                'extraction_method': text_data.get('extraction_method', ''),
                'timestamp': text_data.get('timestamp', ''),
            }
            
            # Add metadata fields if available
            metadata = text_data.get('metadata', {})
            for key, value in metadata.items():
                common_metadata[f'metadata_{key}'] = value
                
            # Process each page's text
            for page_data in text_data.get('text', []):
                page_num = page_data.get('page', 0)
                
                for line in page_data.get('content', []):
                    row = {
                        'page': page_num,
                        'text': line,
                        **common_metadata
                    }
                    flattened_data.append(row)
            
            # Handle the case where no text was extracted
            if not flattened_data:
                logger.warning("No text content extracted to save")
                flattened_data.append({
                    'page': 0,
                    'text': '',
                    **common_metadata,
                    'error': text_data.get('error', 'No text extracted')
                })
            
            # Save to the appropriate format
            output_path = Path(output_file)
            
            if self.output_format == 'csv':
                df = pd.DataFrame(flattened_data)
                df.to_csv(output_path, index=False, encoding='utf-8')
                
            elif self.output_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    # For JSON, we can save the original structure
                    import json
                    json.dump(text_data, f, ensure_ascii=False, indent=2)
                    
            elif self.output_format == 'parquet':
                df = pd.DataFrame(flattened_data)
                df.to_parquet(output_path, index=False)
            
            else:
                # Default to CSV if format not recognized
                df = pd.DataFrame(flattened_data)
                csv_path = output_path.with_suffix('.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8')
                return str(csv_path)
            
            logger.info(f"Saved {len(flattened_data)} text entries to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving output to {output_file}: {str(e)}")
            # Try to save to a fallback location
            fallback_file = f"fallback_output_{int(time.time())}.csv"
            logger.info(f"Attempting to save to fallback file: {fallback_file}")
            
            try:
                df = pd.DataFrame([{'text': f"Error saving original file: {str(e)}"}])
                df.to_csv(fallback_file, index=False)
                return fallback_file
            except:
                logger.critical("Failed to save even to fallback file")
                return ""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Production PDF text extractor")
    
    parser.add_argument('-i', '--input', required=True, 
                        help="Input PDF file or directory containing PDFs")
    parser.add_argument('-o', '--output', 
                        help="Output file or directory (created if doesn't exist)")
    parser.add_argument('-f', '--format', choices=['csv', 'json', 'parquet'], default='csv',
                        help="Output format (default: csv)")
    parser.add_argument('-m', '--method', choices=['pypdf', 'pymupdf', 'auto'], default='auto',
                        help="Text extraction method (default: auto)")
    parser.add_argument('-w', '--workers', type=int, default=4,
                        help="Number of worker threads for directory processing (default: 4)")
    parser.add_argument('--no-metadata', action='store_true',
                        help="Do not include PDF metadata in output")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose logging")
    
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    try:
        args = parse_args()
    except Exception as e:
        logger.error(f"Error parsing arguments: {str(e)}")
        return 1
    
    # Set log level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        # Initialize processor
        processor = PDFProcessor(
            output_format=args.format,
            max_workers=args.workers,
            extraction_method=args.method,
            include_metadata=not args.no_metadata
        )
        
        input_path = Path(args.input)
        
        # Process based on whether input is file or directory
        if input_path.is_file():
            logger.info(f"Processing single file: {input_path}")
            output_file = args.output if args.output else None
            result = processor.process_file(input_path, output_file)
            
            if result:
                logger.info(f"Successfully processed file. Output: {result}")
                return 0
            else:
                logger.error("Failed to process file")
                return 1
                
        elif input_path.is_dir():
            logger.info(f"Processing directory: {input_path}")
            results = processor.process_directory(input_path, args.output)
            
            if results:
                logger.info(f"Successfully processed {len(results)} files")
                return 0
            else:
                logger.error("No files were successfully processed")
                return 1
                
        else:
            logger.error(f"Input path does not exist: {input_path}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())