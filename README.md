
## KlinChainX PDF Processing Pipeline

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
 System Configuration
For optimal performance, configure the following:


1. Environment Variables:
```
export CLEANCHAIN_OUTPUT_DIR=/path/to/output
export CLEANCHAIN_LOG_LEVEL=INFO
export CLEANCHAIN_MAX_WORKERS=8
```

### Usage

#### Command Line Interface
##### Arguments
| Argument       | Description                                                   |
|----------------|---------------------------------------------------------------|
| `-i, --input`  | Input PDF file or directory containing PDFs (required).        |
| `-o, --output` | Output file or directory (created if doesn't exist).           |
| `-f, --format` | Output format: csv, json, or parquet (default: csv).           |
| `-m, --method` | Text extraction method: pypdf, pymupdf, or auto (default: auto). |
| `-w, --workers`| Number of worker threads for directory processing (default: 4).|
| `--no-metadata`| Do not include PDF metadata in output.                         |
| `-v, --verbose`| Enable verbose logging.                                       |
| `-h, --help`   | Show help message.                                            |

##### Examples
- Process a single PDF:  
    `python klinchainx.py -i input.pdf -o output.csv`
- Process a directory of PDFs:  
    `python klinchainx.py -i /path/to/pdfs -o /path/to/output`
- Process with specific options:  
    `python klinchainx.py -i input.pdf -o output.json -f json -m pymupdf`

#### Programmatic API
The API allows integration into custom workflows. Refer to the documentation for detailed examples.

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