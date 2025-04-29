
## KlinChainX 

<img alt="Version" src="https://img.shields.io/badge/version-1.0.0-blue">  
<img alt="Python" src="https://img.shields.io/badge/python-3.9+-green">  
<img alt="License" src="https://img.shields.io/badge/license-MIT-green">  

A robust production-ready PDF text extraction system designed for processing large volumes of documents, with specialized support for West African Pidgin and multilingual content.

### Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
    - [Command Line Interface](#command-line-interface)
    - [Programmatic API](#programmatic-api)
- [Output Formats](#output-formats)
- [Architecture](#architecture)
- [Performance Considerations](#performance-considerations)
- [Integration with RaterX](#integration-with-raterx)
- [Troubleshooting](#troubleshooting)
- [License](#license)

### Overview
KlinChainX PDF Processing Pipeline is a high-performance system built to extract, clean, and normalize text from PDF documents at scale. It's designed to handle large document collections efficiently with multiple extraction engines and robust error handling.

This tool is part of the RaterX ecosystem by StartHub Technologies, specialized for processing West African content including Pidgin language texts.

### Features
- **High-throughput Processing**: Process thousands of documents with multi-threading.
- **Dual Extraction Engines**: Uses both PyMuPDF and PyPDF2 for optimal text quality.
- **Memory-efficient Processing**: Handle large documents using chunking techniques.
- **Parallel Processing**: Multi-threaded operation for batch processing.
- **Multiple Output Formats**: Save as CSV, JSON, or Parquet.
- **Rich Metadata Capture**: Extract and include document metadata.
- **Robust Error Handling**: Continue processing even when individual files fail.
- **Progress Monitoring**: Real-time progress bars for batch operations.
- **Detailed Logging**: Comprehensive tracking of processing activities.

### Installation
#### Prerequisites
- Python 3.9 or higher
- 8GB+ RAM recommended for large document batches

#### Setup
1. Create a `requirements.txt` file with the necessary dependencies.
2. Install dependencies using `pip install -r requirements.txt`.

The requirements include:
```
PyPDF2>=3.0.0
pandas>=2.0.0
numpy>=1.22.0
tqdm>=4.65.0
chardet>=5.0.0
PyMuPDF>=1.22.0
python-dateutil>=2.8.2
pyarrow>=12.0.0  # For parquet support
```
#### System Configuration
For optimal performance, configure the following:

1. Environment Variables:
```bash
export CLEANCHAIN_OUTPUT_DIR=/path/to/output
export CLEANCHAIN_LOG_LEVEL=INFO
export CLEANCHAIN_MAX_WORKERS=8
```

### Usage

#### Command Line Interface
The CLI provides a flexible way to process PDFs. Below are the arguments and their usage:

| Argument       | Description                                                   | Example Usage                                                                 |
|----------------|---------------------------------------------------------------|-------------------------------------------------------------------------------|
| `-i, --input`  | Input PDF file or directory containing PDFs (required).        | `python klinchainx.py -i input.pdf`                                           |
| `-o, --output` | Output file or directory (created if doesn't exist).           | `python klinchainx.py -i input.pdf -o output.csv`                             |
| `-f, --format` | Output format: csv, json, or parquet (default: csv).           | `python klinchainx.py -i input.pdf -o output.json -f json`                    |
| `-m, --method` | Text extraction method: pypdf, pymupdf, or auto (default: auto). | `python klinchainx.py -i input.pdf -m pymupdf`                                |
| `-w, --workers`| Number of worker threads for directory processing (default: 4).| `python klinchainx.py -i /path/to/pdfs -w 8`                                  |
| `--no-metadata`| Do not include PDF metadata in output.                         | `python klinchainx.py -i input.pdf --no-metadata`                             |
| `--text-only`  | Output only the text column with no additional fields.         | `python klinchainx.py -i input.pdf --text-only`                               |
| `-v, --verbose`| Enable verbose logging.                                       | `python klinchainx.py -i input.pdf -v`                                        |
| `-h, --help`   | Show help message.                                            | `python klinchainx.py -h`                                                     |

##### Examples
- Process a single PDF:  
    ```bash
    python klinchainx.py -i input.pdf -o output.csv
    ```
- Process a directory of PDFs:  
    ```bash
    python klinchainx.py -i /path/to/pdfs -o /path/to/output
    ```
- Extract text only:  
    ```bash
    python klinchainx.py -i input.pdf --text-only
    ```

#### Programmatic API
The API allows integration into custom workflows. Below is an example:

```python
from klinchainx import PDFProcessor

processor = PDFProcessor(output_format='json', max_workers=4, extraction_method='pymupdf')
result = processor.process_file('sample.pdf', 'output.json')
print(f"Processed file saved at: {result}")
```

### Output Formats
- **CSV**: Tabular format with columns like `page`, `text`, `filename`, etc.
- **JSON**: Hierarchical format preserving document structure.
- **Parquet**: Columnar format optimized for big data processing.

### Architecture
#### Component Overview
- **Input Validation**: Ensures valid files and directories.
- **Text Extraction**: Uses PyMuPDF (primary) and PyPDF2 (fallback).
- **Metadata Extraction**: Captures PDF metadata.
- **Text Cleaning**: Removes invalid characters and normalizes whitespace.
- **Output Generation**: Formats results for target systems.

#### Processing Flow
1. Validate input files.
2. Extract text and metadata.
3. Clean and normalize text.
4. Generate output in the specified format.

#### Production-Ready Integration Example

Below is a detailed Python script to use KlinChainX in a production-ready setup. This script includes robust error handling, logging, and flexibility for various use cases.

```python
import os
import logging
from klinchainx import PDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("klinchainx.log"),
        logging.StreamHandler()
    ]
)

def process_pdfs(input_path, output_path, output_format="csv", max_workers=4, extraction_method="auto"):
    """
    Process PDFs using KlinChainX with robust error handling and logging.

    Args:
        input_path (str): Path to the input PDF file or directory.
        output_path (str): Path to save the processed output.
        output_format (str): Output format (csv, json, parquet). Default is 'csv'.
        max_workers (int): Number of worker threads for parallel processing. Default is 4.
        extraction_method (str): Text extraction method ('pypdf', 'pymupdf', 'auto'). Default is 'auto'.
    """
    try:
        # Initialize the PDF processor
        processor = PDFProcessor(
            output_format=output_format,
            max_workers=max_workers,
            extraction_method=extraction_method
        )

        # Check if input is a file or directory
        if os.path.isfile(input_path):
            logging.info(f"Processing single file: {input_path}")
            result = processor.process_file(input_path, output_path)
            logging.info(f"Processed file saved at: {result}")
        elif os.path.isdir(input_path):
            logging.info(f"Processing directory: {input_path}")
            results = processor.process_directory(input_path, output_path)
            logging.info(f"Processed files saved at: {results}")
        else:
            logging.error("Invalid input path. Must be a file or directory.")
            return

    except Exception as e:
        logging.error(f"An error occurred during processing: {e}", exc_info=True)

if __name__ == "__main__":
    # Example usage
    input_path = "/path/to/input"
    output_path = "/path/to/output"
    output_format = "json"  # Options: 'csv', 'json', 'parquet'
    max_workers = 8
    extraction_method = "pymupdf"  # Options: 'pypdf', 'pymupdf', 'auto'

    process_pdfs(input_path, output_path, output_format, max_workers, extraction_method)
```


#### Deployment Notes
- **Dockerization**: Package the application in a Docker container for consistent deployment across environments.
- **CI/CD Integration**: Use tools like GitHub Actions to automate testing and deployment.
- **Monitoring**: Integrate logging and monitoring tools like ELK Stack or Prometheus for production environments.
- **Scalability**: Use cloud services like AWS Lambda or Azure Functions for serverless processing of large document batches.

### Performance Considerations
#### Resource Requirements
| Operation          | CPU       | RAM       | Disk Space |
|---------------------|-----------|-----------|------------|
| Single PDF (200pg)  | 1-2 cores | 500MB     | 10MB       |
| Batch (1000 PDFs)   | 8+ cores  | 8GB+      | 5GB+       |

#### Optimization Tips
- Adjust `max_workers` based on available CPU cores.
- Use `parquet` format for large datasets.
- Set `extraction_method='pymupdf'` for best quality.

### Integration with RaterX
KlinChainX PDF Processing Pipeline integrates seamlessly with RaterX vector database systems, enabling efficient storage and retrieval of processed text data.

### Troubleshooting
#### Common Issues
- **Memory Errors**: Reduce chunk size or increase available memory.
- **Text Extraction Quality Issues**: Try different extraction methods.
- **Parallel Processing Errors**: Reduce worker count.

#### Logs
Check the log file for detailed information on processing activities.

### License
This project is licensed under the MIT License. See the LICENSE file for details.

KlinChainX PDF Processing Pipeline is part of the RaterX ecosystem by StartHub Technologies.
