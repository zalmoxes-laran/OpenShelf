"""
OpenShelf UI Timer Utilities
Utilità per gestione timer e aggiornamenti UI non-bloccanti
Centralizza la logica per operazioni modal responsive
"""

import bpy
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class UIState:
    """Stato UI per operazioni asincrone"""
    is_active: bool = False
    progress: float = 0.0
    status_message: str = ""
    last_update: float = 0.0
    start_time: float = 0.0
    
    def reset(self):
        """Reset dello stato"""
        self.is_active = False
        self.progress = 0.0
        self.status_message = ""
        self.last_update = 0.0
        self.start_time = time.time()
    
    def update_progress(self, progress: float, message: str = None):
        """Aggiorna progress e messaggio"""
        self.progress = max(0.0, min(100.0, progress))
        if message:
            self.status_message = message
        self.last_update = time.time()


class ResponsiveTimer:
    """Timer responsivo per operazioni modal non-bloccanti"""
    
    def __init__(self, context, timer_interval: float = 0.02):
        """
        Inizializza timer responsivo
        
        Args:
            context: Blender context
            timer_interval: Intervallo timer in secondi (default 50 FPS)
        """
        self.context = context
        self.timer_interval = timer_interval
        self.timer = None
        self.ui_state = UIState()
        self.ui_update_interval = 0.05  # 20 FPS per UI updates
        self.last_ui_update = 0.0
        
        # Callbacks
        self.step_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
        self.complete_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
    def start(self, step_callback: Callable, 
              progress_callback: Optional[Callable] = None,
              complete_callback: Optional[Callable] = None,
              error_callback: Optional[Callable] = None) -> bool:
        """
        Avvia il timer con callbacks
        
        Args:
            step_callback: Funzione chiamata ad ogni timer tick
            progress_callback: Callback per aggiornamenti progress
            complete_callback: Callback per completamento
            error_callback: Callback per errori
        """
        try:
            if self.timer:
                self.stop()
            
            self.step_callback = step_callback
            self.progress_callback = progress_callback
            self.complete_callback = complete_callback
            self.error_callback = error_callback
            
            self.ui_state.reset()
            self.ui_state.is_active = True
            
            # Avvia timer
            wm = self.context.window_manager
            self.timer = wm.event_timer_add(self.timer_interval, window=self.context.window)
            
            print(f"ResponsiveTimer: Started with {1/self.timer_interval:.0f} FPS timer")
            return True
            
        except Exception as e:
            print(f"ResponsiveTimer: Failed to start timer: {e}")
            if self.error_callback:
                self.error_callback(str(e))
            return False
    
    def stop(self):
        """Ferma il timer"""
        if self.timer:
            try:
                wm = self.context.window_manager
                wm.event_timer_remove(self.timer)
                print("ResponsiveTimer: Timer stopped")
            except Exception as e:
                print(f"ResponsiveTimer: Error stopping timer: {e}")
            finally:
                self.timer = None
        
        self.ui_state.is_active = False
    
    def process_timer_event(self) -> Dict[str, Any]:
        """
        Processa evento timer
        
        Returns:
            Dict con risultato del processing
        """
        current_time = time.time()
        result = {'should_continue': True, 'ui_updated': False}
        
        try:
            # Chiama step callback
            if self.step_callback:
                step_result = self.step_callback(self.ui_state)
                
                if isinstance(step_result, dict):
                    result.update(step_result)
                elif step_result is False:
                    result['should_continue'] = False
            
            # Aggiorna UI se necessario (throttled)
            if current_time - self.last_ui_update > self.ui_update_interval:
                self.update_ui()
                result['ui_updated'] = True
                self.last_ui_update = current_time
            
            # Chiama progress callback se presente
            if self.progress_callback and result['ui_updated']:
                self.progress_callback(self.ui_state.progress, self.ui_state.status_message)
        
        except Exception as e:
            print(f"ResponsiveTimer: Error in timer processing: {e}")
            result['should_continue'] = False
            result['error'] = str(e)
            
            if self.error_callback:
                self.error_callback(str(e))
        
        # Se non deve continuare, ferma il timer
        if not result['should_continue']:
            self.stop()
            
            if result.get('error'):
                if self.error_callback:
                    self.error_callback(result['error'])
            else:
                if self.complete_callback:
                    self.complete_callback(self.ui_state)
        
        return result
    
    def update_ui(self):
        """Aggiorna UI usando lo stato corrente"""
        try:
            scene = self.context.scene
            
            # Aggiorna proprietà scene per progress panel
            if hasattr(scene, 'openshelf_download_progress'):
                scene.openshelf_download_progress = int(self.ui_state.progress)
            
            if hasattr(scene, 'openshelf_status_message'):
                scene.openshelf_status_message = self.ui_state.status_message
            
            if hasattr(scene, 'openshelf_is_downloading'):
                scene.openshelf_is_downloading = self.ui_state.is_active
            
            # Force redraw delle aree rilevanti
            self.force_ui_redraw()
            
        except Exception as e:
            print(f"ResponsiveTimer: UI update error: {e}")
    
    def force_ui_redraw(self):
        """Force redraw ottimizzato dell'UI"""
        try:
            # Update window manager
            if hasattr(self.context, 'window_manager'):
                self.context.window_manager.update_tag()
            
            # Update solo aree 3D (dove sono i nostri pannelli)
            if hasattr(self.context, 'screen') and hasattr(self.context.screen, 'areas'):
                for area in self.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                        # Update regione UI specifica
                        for region in area.regions:
                            if region.type == 'UI':
                                region.tag_redraw()
                                break
        
        except Exception as e:
            print(f"ResponsiveTimer: Force redraw error: {e}")
    
    def set_progress(self, progress: float, message: str = None):
        """Imposta progress e messaggio"""
        self.ui_state.update_progress(progress, message)
    
    def get_elapsed_time(self) -> float:
        """Restituisce tempo trascorso dall'inizio"""
        return time.time() - self.ui_state.start_time
    
    def is_active(self) -> bool:
        """Verifica se il timer è attivo"""
        return self.timer is not None and self.ui_state.is_active


class ModalOperatorMixin:
    """Mixin per operatori modal con timer responsivo"""
    
    def __init__(self):
        self._responsive_timer: Optional[ResponsiveTimer] = None
        self._timeout = 300  # 5 minuti default
    
    def start_responsive_timer(self, context, step_callback: Callable,
                             progress_callback: Optional[Callable] = None,
                             complete_callback: Optional[Callable] = None,
                             error_callback: Optional[Callable] = None,
                             timer_interval: float = 0.02) -> bool:
        """Avvia timer responsivo"""
        self._responsive_timer = ResponsiveTimer(context, timer_interval)
        
        return self._responsive_timer.start(
            step_callback=step_callback,
            progress_callback=progress_callback,
            complete_callback=complete_callback or self._default_complete_callback,
            error_callback=error_callback or self._default_error_callback
        )
    
    def stop_responsive_timer(self):
        """Ferma timer responsivo"""
        if self._responsive_timer:
            self._responsive_timer.stop()
            self._responsive_timer = None
    
    def process_timer_event_responsive(self) -> Dict[str, Any]:
        """Processa evento timer responsivo"""
        if self._responsive_timer:
            return self._responsive_timer.process_timer_event()
        return {'should_continue': False}
    
    def set_progress_responsive(self, progress: float, message: str = None):
        """Imposta progress nel timer responsivo"""
        if self._responsive_timer:
            self._responsive_timer.set_progress(progress, message)
    
    def is_timer_active_responsive(self) -> bool:
        """Verifica se timer responsivo è attivo"""
        return self._responsive_timer and self._responsive_timer.is_active()
    
    def get_elapsed_time_responsive(self) -> float:
        """Tempo trascorso nel timer responsivo"""
        if self._responsive_timer:
            return self._responsive_timer.get_elapsed_time()
        return 0.0
    
    def check_timeout_responsive(self) -> bool:
        """Controlla se è scaduto il timeout"""
        return self.get_elapsed_time_responsive() > self._timeout
    
    def _default_complete_callback(self, ui_state: UIState):
        """Callback di default per completamento"""
        print(f"ResponsiveTimer: Operation completed in {ui_state.last_update - ui_state.start_time:.1f}s")
    
    def _default_error_callback(self, error_message: str):
        """Callback di default per errori"""
        print(f"ResponsiveTimer: Operation failed: {error_message}")


class UIStateManager:
    """Manager globale per stato UI di OpenShelf"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.active_operations = {}  # operation_id -> UIState
            self.global_ui_state = UIState()
            self._initialized = True
    
    def register_operation(self, operation_id: str, ui_state: UIState):
        """Registra un'operazione attiva"""
        self.active_operations[operation_id] = ui_state
        self._update_global_state()
    
    def unregister_operation(self, operation_id: str):
        """Deregistra un'operazione"""
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
            self._update_global_state()
    
    def _update_global_state(self):
        """Aggiorna stato globale basato su operazioni attive"""
        if not self.active_operations:
            self.global_ui_state.reset()
            return
        
        # Calcola stato combinato
        total_progress = sum(state.progress for state in self.active_operations.values())
        avg_progress = total_progress / len(self.active_operations)
        
        # Usa messaggio dell'operazione più recente
        latest_state = max(self.active_operations.values(), key=lambda s: s.last_update)
        
        self.global_ui_state.is_active = True
        self.global_ui_state.progress = avg_progress
        self.global_ui_state.status_message = latest_state.status_message
        self.global_ui_state.last_update = time.time()
    
    def get_global_state(self) -> UIState:
        """Restituisce stato globale"""
        return self.global_ui_state
    
    def has_active_operations(self) -> bool:
        """Verifica se ci sono operazioni attive"""
        return len(self.active_operations) > 0
    
    def cancel_all_operations(self):
        """Cancella tutte le operazioni attive"""
        self.active_operations.clear()
        self.global_ui_state.reset()


# Singleton per accesso globale
def get_ui_state_manager() -> UIStateManager:
    """Restituisce istanza singleton del manager"""
    return UIStateManager()


# Utility functions
def safe_ui_update(context, force_redraw: bool = True):
    """Aggiornamento UI sicuro"""
    try:
        if hasattr(context, 'window_manager'):
            context.window_manager.update_tag()
        
        if force_redraw and hasattr(context, 'screen'):
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    
    except Exception as e:
        print(f"Safe UI update error: {e}")


def setup_scene_properties(scene):
    """Setup delle proprietà scene necessarie se non esistono"""
    try:
        # Verifica e crea proprietà necessarie
        if not hasattr(scene, 'openshelf_is_downloading'):
            scene.openshelf_is_downloading = False
        
        if not hasattr(scene, 'openshelf_download_progress'):
            scene.openshelf_download_progress = 0
        
        if not hasattr(scene, 'openshelf_status_message'):
            scene.openshelf_status_message = ""
            
    except Exception as e:
        print(f"Scene properties setup error: {e}")


def cleanup_scene_properties(scene):
    """Pulizia proprietà scene"""
    try:
        scene.openshelf_is_downloading = False
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = ""
        
    except Exception as e:
        print(f"Scene properties cleanup error: {e}")