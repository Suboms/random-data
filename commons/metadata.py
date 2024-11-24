from rest_framework.metadata import BaseMetadata


class MinimalMetadata(BaseMetadata):
    def determine_metadata(self, request, view):
        return {
            "name": view.get_view_name(),
            "description": view.get_view_description(),
            "renders": [renderer.media_type for renderer in view.renderer_classes],
            "parses": [parser.media_type for parser in view.parser_classes],
        }
