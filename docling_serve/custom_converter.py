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

        parser_config = ParserConfig(
            layout_batch_size=config.layout_batch_size or 32,
            table_batch_size=config.table_batch_size or 32,
        )

        self.doc_tool = DocTool(config=parser_config)
        _log.info(f"[CustomConverter] Configured with layout_batch_size={parser_config.layout_batch_size}, table_batch_size={parser_config.table_batch_size}")

    def clear_cache(self):
        """Clear any cached converters (no-op for custom implementation)."""
        _log.debug("[CustomConverter] Cache clear requested (no-op)")

    def get_pdf_pipeline_opts(self, request: ConvertDocumentsOptions):
        """
        Return dummy pipeline options for compatibility.
        This is called by LocalOrchestrator.warm_up_caches() but not used in custom converter.
        """
        from docling.document_converter import PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        _log.debug("[CustomConverter] get_pdf_pipeline_opts called (returning dummy options)")
        return PdfFormatOption(
            pipeline_options=PdfPipelineOptions(),
            backend=PyPdfiumDocumentBackend
        )

    def get_converter(self, pdf_format_option):
        """
        Return dummy converter for compatibility.
        This is called by LocalOrchestrator.warm_up_caches() but not used in custom converter.
        """
        from docling.document_converter import DocumentConverter

        _log.debug("[CustomConverter] get_converter called (returning dummy converter)")
        return DocumentConverter()

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

    def _create_conversion_result(self, custom_doc, options: ConvertDocumentsOptions) -> ConversionResult:
        """
        Convert custom Document object to docling's ConversionResult format.

        This creates a compatibility layer between the custom parser output
        and what docling_serve expects.
        """
        from docling.datamodel.document import ConversionResult, ConversionStatus, InputDocument
        from docling_core.types.doc import DoclingDocument, TextItem

        # Create a minimal DoclingDocument from custom output
        docling_doc = DoclingDocument(name=custom_doc.id)

        # Add the markdown text as a text item
        # This is a simplified conversion - extend as needed
        text_item = TextItem(text=custom_doc.text)
        docling_doc.add_text(text_item)
        
        # CRITICAL: Override export_to_markdown to return our custom markdown
        custom_markdown_text = custom_doc.text
        def custom_export_to_markdown(*args, **kwargs):
            return custom_markdown_text

        docling_doc.export_to_markdown = custom_export_to_markdown

        # Store custom images in the document's metadata if needed
        # The images are already base64-encoded in custom_doc.images

        # Create input document info
        input_doc = InputDocument(
            file=DocumentStream(name=custom_doc.id, stream=BytesIO(b"")),
            format=None,
        )

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
