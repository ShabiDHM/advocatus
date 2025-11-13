# FILE: backend/app/services/conversion_service.py

import logging
import os
import subprocess
import tempfile
import shutil

logger = logging.getLogger(__name__)

def convert_to_pdf(source_path: str) -> str:
    """
    Converts a given document file to a PDF using LibreOffice.

    If the source file is already a PDF, it returns a path to a copy. Otherwise,
    it uses the 'soffice' command-line tool for conversion. This function is
    designed to run within a container where LibreOffice is installed.

    Args:
        source_path: The absolute path to the source document.

    Returns:
        The absolute path to the newly created PDF file.

    Raises:
        FileNotFoundError: If the source_path does not exist.
        RuntimeError: If the conversion command fails or soffice is not found.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found at path: {source_path}")

    file_name, source_ext = os.path.splitext(os.path.basename(source_path))
    
    # If the file is already a PDF, create a copy and return its path.
    if source_ext.lower() == '.pdf':
        logger.info(f"Source file '{file_name}{source_ext}' is already a PDF. Bypassing conversion.")
        dest_pdf_path = os.path.join(tempfile.gettempdir(), f"{file_name}_preview.pdf")
        shutil.copy2(source_path, dest_pdf_path)
        return dest_pdf_path

    logger.info(f"Initiating PDF conversion for '{file_name}{source_ext}'.")

    output_dir = tempfile.gettempdir()
    
    command = [
        "soffice",
        "--headless",
        "--convert-to", "pdf:writer_pdf_Export",
        "--outdir", output_dir,
        source_path,
    ]

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120  # 2-minute timeout
        )

        if process.returncode != 0:
            stderr_output = process.stderr.decode('utf-8', errors='ignore')
            error_message = f"LibreOffice conversion failed with exit code {process.returncode}. Stderr: {stderr_output}"
            logger.error(error_message)
            raise RuntimeError(error_message)

        expected_output_path = os.path.join(output_dir, f"{file_name}.pdf")

        if not os.path.exists(expected_output_path):
            error_message = f"Conversion command succeeded but output PDF not found at expected path: '{expected_output_path}'."
            logger.error(error_message)
            raise RuntimeError(error_message)
            
        # --- PHOENIX PROTOCOL CURE: ADDED FILE VALIDATION ---
        # Verify that the created file is not empty (a common failure mode).
        if os.path.getsize(expected_output_path) == 0:
            error_message = f"Conversion produced a zero-byte (empty) PDF file. The source file may be unsupported or corrupt."
            logger.error(error_message)
            os.remove(expected_output_path) # Clean up the empty file
            raise RuntimeError(error_message)

        logger.info(f"Successfully converted '{os.path.basename(source_path)}' to '{os.path.basename(expected_output_path)}'.")
        return expected_output_path

    except FileNotFoundError:
        logger.critical("!!! CRITICAL: The `soffice` command was not found. LibreOffice must be installed in the Docker container.")
        raise RuntimeError("Conversion tool 'soffice' is not installed or not in the system's PATH.")
    except subprocess.TimeoutExpired:
        logger.error(f"PDF conversion for '{os.path.basename(source_path)}' timed out after 120 seconds.")
        raise RuntimeError("PDF conversion process timed out.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during PDF conversion: {e}", exc_info=True)
        raise