"""
OpenShelf Viewport Panels
Pannelli aggiuntivi nel viewport 3D
"""

import bpy
from bpy.types import Panel


class OPENSHELF_PT_statistics_panel(Panel):
    """Pannello statistiche repository"""
    bl_label = "Repository Statistics"
    bl_idname = "OPENSHELF_PT_statistics_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 9
    bl_options = {'DEFAULT_CLOSED'}  # Chiuso di default per non occupare spazio

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Pulsante per ottenere statistiche
        box = layout.box()
        box.label(text="Repository Info", icon='GRAPH')

        col = box.column(align=True)
        col.operator("openshelf.repository_statistics", text="View Full Statistics", icon='GRAPH')
        col.operator("openshelf.registry_status", text="Registry Status", icon='INFO')

        # Statistiche rapide se disponibili nei risultati correnti
        if hasattr(scene, 'openshelf_search_results') and scene.openshelf_search_results:
            box = layout.box()
            box.label(text="Current Results", icon='PRESET')

            col = box.column(align=True)
            col.scale_y = 0.8

            # Conta risultati per tipo
            type_counts = {}
            repo_counts = {}
            quality_scores = []

            for result in scene.openshelf_search_results:
                # Tipo oggetto
                obj_type = result.object_type or "N/D"
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

                # Repository
                repo = result.repository or "Unknown"
                repo_counts[repo] = repo_counts.get(repo, 0) + 1

                # Qualità
                if result.quality_score > 0:
                    quality_scores.append(result.quality_score)

            # Mostra conteggi
            col.label(text=f"Total results: {len(scene.openshelf_search_results)}")

            if len(repo_counts) > 1:
                col.label(text="By repository:")
                for repo, count in sorted(repo_counts.items(), key=lambda x: x[1], reverse=True):
                    col.label(text=f"  • {repo}: {count}")

            if len(type_counts) > 1:
                col.label(text="By type:")
                top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                for obj_type, count in top_types:
                    col.label(text=f"  • {obj_type}: {count}")

                if len(type_counts) > 3:
                    col.label(text=f"  ... and {len(type_counts) - 3} more")

            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                col.label(text=f"Avg quality: {avg_quality:.0f}%")


        # Cache info concisa (senza pulsanti duplicati)
        box = layout.box()
        box.label(text="Cache Info", icon='FILE_CACHE')

        col = box.column(align=True)
        col.scale_y = 0.8

        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()
            cache_stats = dm.get_cache_statistics()

            col.label(text=f"Cache: {cache_stats['file_count']} files")
            cache_size_mb = cache_stats['cache_size'] / (1024*1024)
            col.label(text=f"Size: {cache_size_mb:.1f} MB")

        except Exception:
            col.label(text="Cache: Not available")

        # Link alle preferenze per gestione cache
        col.separator()
        col.operator("preferences.addon_show", text="Manage Cache", icon='PREFERENCES').module = __package__.split('.')[0]

        '''
        # Info cache
        box = layout.box()
        box.label(text="Cache Info", icon='FILE_CACHE')

        col = box.column(align=True)
        col.scale_y = 0.8

        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()
            cache_stats = dm.get_cache_statistics()

            col.label(text=f"Cache: {cache_stats['file_count']} files")
            cache_size_mb = cache_stats['cache_size'] / (1024*1024)
            col.label(text=f"Size: {cache_size_mb:.1f} MB")

        except Exception:
            col.label(text="Cache: Not available")

        # Azioni pulizia
        row = col.row(align=True)
        row.scale_y = 0.8
        clear_op = row.operator("openshelf.clear_repository_cache", text="Clear", icon='TRASH')
        clear_op.repository_name = "all"
        clear_op.confirm = True
        '''

class OPENSHELF_PT_object_info(Panel):
    """Pannello informazioni oggetto OpenShelf"""
    bl_label = "Cultural Asset Info"
    bl_idname = "OPENSHELF_PT_object_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 7

    @classmethod
    def poll(cls, context):
        """Mostra solo se oggetto attivo ha metadati OpenShelf"""
        obj = context.active_object
        return obj and any(key.startswith('openshelf_') for key in obj.keys())

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj:
            return

        # Trova metadati OpenShelf
        openshelf_props = {k: v for k, v in obj.items() if k.startswith('openshelf_')}

        if not openshelf_props:
            return

        # Informazioni base
        box = layout.box()
        box.label(text="Asset Information", icon='INFO')

        # Nome e ID
        if 'openshelf_name' in openshelf_props:
            box.label(text=f"Name: {openshelf_props['openshelf_name']}")

        if 'openshelf_id' in openshelf_props:
            box.label(text=f"ID: {openshelf_props['openshelf_id']}")

        # Repository e tipo
        if 'openshelf_repository' in openshelf_props:
            box.label(text=f"Repository: {openshelf_props['openshelf_repository']}")

        if 'openshelf_object_type' in openshelf_props:
            box.label(text=f"Type: {openshelf_props['openshelf_object_type']}")

        # Numero inventario
        if 'openshelf_inventory_number' in openshelf_props:
            box.label(text=f"Inventory: {openshelf_props['openshelf_inventory_number']}")

        # Descrizione
        if 'openshelf_description' in openshelf_props:
            description = openshelf_props['openshelf_description']
            if len(description) > 100:
                description = description[:100] + "..."
            box.label(text=f"Description:")

            # Spezza descrizione in righe
            words = description.split(' ')
            current_line = ""
            for word in words:
                if len(current_line + word) > 40:
                    if current_line:
                        box.label(text=f"  {current_line}")
                        current_line = word
                    else:
                        box.label(text=f"  {word}")
                else:
                    current_line += " " + word if current_line else word

            if current_line:
                box.label(text=f"  {current_line}")

        # Dettagli culturali
        box = layout.box()
        box.label(text="Cultural Details", icon='BOOKMARKS')

        # Materiali
        if 'openshelf_materials' in openshelf_props:
            materials = openshelf_props['openshelf_materials']
            box.label(text=f"Materials: {materials}")

        # Cronologia
        if 'openshelf_chronology' in openshelf_props:
            chronology = openshelf_props['openshelf_chronology']
            box.label(text=f"Period: {chronology}")

        # Provenienza
        if 'openshelf_provenance' in openshelf_props:
            provenance = openshelf_props['openshelf_provenance']
            box.label(text=f"Provenance: {provenance}")

        # Informazioni tecniche
        box = layout.box()
        box.label(text="Technical Info", icon='SETTINGS')

        # Qualità
        if 'openshelf_quality_score' in openshelf_props:
            quality = openshelf_props['openshelf_quality_score']
            box.label(text=f"Quality Score: {quality}%")

        # Formato file
        if 'openshelf_file_format' in openshelf_props:
            file_format = openshelf_props['openshelf_file_format']
            box.label(text=f"Format: {file_format.upper()}")

        # Dimensione file
        if 'openshelf_file_size' in openshelf_props:
            file_size = openshelf_props['openshelf_file_size']
            box.label(text=f"File Size: {file_size} KB")

        # Texture
        if 'openshelf_has_textures' in openshelf_props:
            has_textures = openshelf_props['openshelf_has_textures']
            texture_icon = 'CHECKMARK' if has_textures else 'X'
            box.label(text=f"Textures: {'Yes' if has_textures else 'No'}", icon=texture_icon)

        # Timestamp import
        if 'openshelf_import_timestamp' in openshelf_props:
            timestamp = openshelf_props['openshelf_import_timestamp']
            box.label(text=f"Imported: Frame {timestamp}")

        # Link esterni
        if any(key in openshelf_props for key in ['openshelf_detail_url', 'openshelf_catalog_url']):
            box = layout.box()
            box.label(text="External Links", icon='URL')

            # Questi sarebbero bottoni che aprono URL (non implementato)
            if 'openshelf_detail_url' in openshelf_props:
                box.label(text="• Detail Page Available")

            if 'openshelf_catalog_url' in openshelf_props:
                box.label(text="• Catalog Entry Available")

class OPENSHELF_PT_quick_actions(Panel):
    """Pannello azioni rapide"""
    bl_label = "Quick Actions"
    bl_idname = "OPENSHELF_PT_quick_actions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Ricerche rapide
        box = layout.box()
        box.label(text="Quick Search", icon='ZOOM_SELECTED')

        # Bottoni ricerca predefinita
        col = box.column(align=True)

        # Ricerca per tipo oggetto comune
        row = col.row(align=True)
        anello_op = row.operator("openshelf.quick_search", text="Rings")
        anello_op.search_term = "anello"
        anello_op.search_field = "object_type"

        vaso_op = row.operator("openshelf.quick_search", text="Vases")
        vaso_op.search_term = "vaso"
        vaso_op.search_field = "object_type"

        # Ricerca per materiale
        row = col.row(align=True)
        oro_op = row.operator("openshelf.quick_search", text="Gold")
        oro_op.search_term = "oro"
        oro_op.search_field = "material"

        argilla_op = row.operator("openshelf.quick_search", text="Clay")
        argilla_op.search_term = "argilla"
        argilla_op.search_field = "material"

        # Ricerca per periodo
        row = col.row(align=True)
        sec1_op = row.operator("openshelf.quick_search", text="1st Century")
        sec1_op.search_term = "sec. I"
        sec1_op.search_field = "chronology"

        romano_op = row.operator("openshelf.quick_search", text="Roman")
        romano_op.search_term = "roman"
        romano_op.search_field = "search"

        # Gestione cache
        #box = layout.box()
        #box.label(text="Cache Management", icon='FILE_CACHE')

        #col = box.column(align=True)
        #clear_op = col.operator("openshelf.clear_repository_cache", text="Clear Cache", icon='TRASH')
        #clear_op.repository_name = "all"
        #clear_op.confirm = True

        # Utilità
        box = layout.box()
        box.label(text="Utilities", icon='TOOL_SETTINGS')

        col = box.column(align=True)
        col.operator("openshelf.export_repository_config", text="Export Config", icon='EXPORT')
        col.operator("openshelf.add_custom_repository", text="Add Repository", icon='ADD')

class OPENSHELF_PT_help_panel(Panel):
    """Pannello aiuto"""
    bl_label = "Help"
    bl_idname = "OPENSHELF_PT_help_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 10

    def draw(self, context):
        layout = self.layout

        # Guida rapida
        box = layout.box()
        box.label(text="Quick Guide", icon='HELP')

        col = box.column(align=True)
        col.scale_y = 0.8

        col.label(text="1. Select repository")
        col.label(text="2. Enter search terms")
        col.label(text="3. Apply filters if needed")
        col.label(text="4. Click Search")
        col.label(text="5. Import desired assets")

        # Suggerimenti
        box = layout.box()
        box.label(text="Tips", icon='OUTLINER_OB_LIGHT')

        col = box.column(align=True)
        col.scale_y = 0.8

        col.label(text="• Use specific terms for better results")
        col.label(text="• Try different repositories")
        col.label(text="• Check asset quality before import")
        col.label(text="• Use filters to narrow results")
        col.label(text="• Clear cache if issues occur")

        # Informazioni versione
        box = layout.box()
        box.label(text="Version Info", icon='INFO')

        col = box.column(align=True)
        col.scale_y = 0.8

        col.label(text="OpenShelf v1.0.0")
        col.label(text="Cultural Heritage Assets")
        col.label(text="GPL-3.0-or-later")

# Lista pannelli da registrare
panels = [
    OPENSHELF_PT_object_info,
    OPENSHELF_PT_quick_actions,
    OPENSHELF_PT_statistics_panel,
    OPENSHELF_PT_help_panel,
]

def register():
    """Registra i pannelli viewport"""
    for panel in panels:
        bpy.utils.register_class(panel)

def unregister():
    """Deregistra i pannelli viewport"""
    for panel in reversed(panels):
        bpy.utils.unregister_class(panel)
