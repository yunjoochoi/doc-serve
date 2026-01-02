"""
Custom Document Converter Manager that wraps DocTool from docling_test.py
This replaces DoclingConverterManager to use custom parsing logic while maintaining API compatibility.
"""

import logging
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Union

from docling.datamodel.base_models import DocumentStream
from docling.datamodel.document import ConversionResult
from docling_jobkit.convert.manager import DoclingConverterManagerConfig
from docling_jobkit.datamodel.convert import ConvertDocumentsOptions
from docling_serve.docling_test import DocTool

_log = logging.getLogger(__name__)


class CustomConverterManager:
    """
    Custom converter manager that uses DocTool from docling_test.py
    Maintains the same interface as DoclingConverterManager for drop-in replacement.
    """

    def __init__(self, config: DoclingConverterManagerConfig):
        self.config = config
        _log.info("[CustomConverter] Initializing custom converter manager")

        # Import ParserConfig and configure with settings from config
        from docling_serve.docling_test import ParserConfig

        # Use ParserConfig defaults, override only if explicitly set in config
        parser_kwargs = {}
        if config.layout_batch_size is not None:
            parser_kwargs['layout_batch_size'] = config.layout_batch_size
        if config.table_batch_size is not None:
            parser_kwargs['table_batch_size'] = config.table_batch_size

        parser_config = ParserConfig(**parser_kwargs)

        self.doc_tool = DocTool(config=parser_config)
        _log.info(
            f"[CustomConverter] Configured with: "
            f"do_ocr={parser_config.do_ocr}, "
            f"do_table_structure={parser_config.do_table_structure}, "
            f"generate_picture_images={parser_config.generate_picture_images}, "
            f"images_scale={parser_config.images_scale}, "
            f"layout_batch_size={parser_config.layout_batch_size}, "
            f"table_batch_size={parser_config.table_batch_size}, "
            f"doc_batch_size={parser_config.doc_batch_size}, "
            f"doc_batch_concurrency={parser_config.doc_batch_concurrency}"
        )

    def clear_cache(self):
        """Clear any cached converters (no-op for custom implementation)."""
        _log.debug("[CustomConverter] Cache clear requested (no-op)")

    def get_pdf_pipeline_opts(self, request: ConvertDocumentsOptions):
        """
        Return pipeline options with artifacts_path for compatibility.
        This is called by LocalOrchestrator.warm_up_caches().
        """
        from docling.document_converter import PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        _log.debug(f"[CustomConverter] get_pdf_pipeline_opts called (artifacts_path={self.config.artifacts_path})")
        return PdfFormatOption(
            pipeline_options=PdfPipelineOptions(artifacts_path=self.config.artifacts_path),
            backend=PyPdfiumDocumentBackend
        )

    def get_converter(self, pdf_format_option):
        """
        Return converter with proper artifacts_path for compatibility.
        This is called by LocalOrchestrator.warm_up_caches().
        """
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat

        _log.debug(f"[CustomConverter] get_converter called (using pdf_format_option with artifacts_path)")
        return DocumentConverter(
            format_options={InputFormat.PDF: pdf_format_option}
        )

    def convert_documents(
        self,
        sources: Iterable[Union[Path, str, DocumentStream]],
        options: ConvertDocumentsOptions,
        headers: Optional[dict[str, Any]] = None,
    ) -> Iterable[ConversionResult]:
        """
        Convert documents using custom DocTool logic.

        This method intercepts the standard docling conversion flow and uses
        the custom parsing logic from docling_test.py instead.
        """
        _log.info("[CustomConverter] Starting custom document conversion")

        # Convert sources to file_dict format expected by DocTool
        file_dict = {}
        source_list = list(sources)

        for source in source_list:
            if isinstance(source, DocumentStream):
                # Already a stream - use it directly
                filename = source.name
                source.stream.seek(0)
                file_dict[filename] = BytesIO(source.stream.read())
            elif isinstance(source, (Path, str)):
                # File path - read it
                path = Path(source)
                filename = path.name
                with open(path, "rb") as f:
                    file_dict[filename] = BytesIO(f.read())
            else:
                _log.warning(f"[CustomConverter] Unsupported source type: {type(source)}")
                continue

        _log.info(f"[CustomConverter] Processing {len(file_dict)} documents")

        # Use custom DocTool to parse
        custom_results = self.doc_tool.run(file_dict)

        # Convert custom Document objects back to ConversionResult format
        # This is a compatibility layer to match docling's expected output
        for custom_doc in custom_results:
            # Create a mock ConversionResult that wraps our custom output
            # The orchestrator expects ConversionResult objects
            result = self._create_conversion_result(custom_doc, options)
            yield result

    def _create_conversion_result(self, custom_doc, options: ConvertDocumentsOptions):
        """
        Convert custom Document object to docling's ConversionResult format.

        This creates a compatibility layer between the custom parser output
        and what docling_serve expects.
        """
        from docling.datamodel.document import ConversionResult, ConversionStatus, InputDocument
        from docling.datamodel.base_models import InputFormat
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling_core.types.doc import DoclingDocument

        # Create a wrapper class that overrides export_to_markdown
        class CustomDoclingDocument(DoclingDocument):
            _custom_markdown: str = ""

            def export_to_markdown(self, *args, **kwargs) -> str:
                return self._custom_markdown

        # Create document with custom markdown
        docling_doc = CustomDoclingDocument(name=custom_doc.id)
        docling_doc._custom_markdown = custom_doc.text

        # Create a mock InputDocument using model_construct to bypass Pydantic validation
        # This avoids actually opening the PDF file
        input_doc = InputDocument.model_construct(
            path_or_stream=BytesIO(b"%PDF-1.4"),  # Minimal valid PDF header
            format=InputFormat.PDF,
            backend=PyPdfiumDocumentBackend,
            filename=custom_doc.id,
            valid=True,
            limits=None,
        )
        # Manually set the file attribute for compatibility
        input_doc.file = type('obj', (object,), {'name': custom_doc.id})()

        # Create conversion result
        result = ConversionResult(
            input=input_doc,
            document=docling_doc,
            status=ConversionStatus.SUCCESS,
        )

        # Store custom data in result for later retrieval
        result._custom_markdown = custom_doc.text
        result._custom_images = custom_doc.images

        _log.info(f"[CustomConverter] Converted {custom_doc.id} with {len(custom_doc.images or [])} images")

        return result
