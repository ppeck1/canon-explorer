from .colors import ThemePalette, get_theme, list_themes, THEMES
from .view_registry import ViewRenderer, register_view, get_view, list_views, instantiate_view

# Import all view modules to trigger @register_view decorators
from . import physical_views
from . import informational_views
from . import canon_views
from . import scope_views
