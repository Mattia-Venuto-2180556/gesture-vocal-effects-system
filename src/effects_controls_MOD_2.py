import mido

class EffectsControllerMOD2:
    def __init__(self, port_name="IAC Driver Bus 1"):
        try:
            self.outport = mido.open_output(port_name)
        except Exception as e:
            print(f"Errore apertura porta MIDI: {e}")
            self.outport = None

        self.EFFECT_CC_MAP = {
            "EFFECT_1": 20,
            "EFFECT_2": 21,
            "EFFECT_3": 22
        }

        self.last_sent = {
            "EFFECT_1": None,
            "EFFECT_2": None,
            "EFFECT_3": None
        }

    def _scale_value(self, value, start, end):
        value = max(0, min(127, value))
        scaled = int(start + (value / 127) * (end - start))
        lower, upper = min(start, end), max(start, end)
        return max(lower, min(upper, scaled))

    def send_modulation(self, selected_effect, value):
        if selected_effect == "NONE" or not self.outport:
            return

        if selected_effect not in self.EFFECT_CC_MAP:
            return

        cc_number = self.EFFECT_CC_MAP[selected_effect]

        # Se EFFECT_3 in Logic richiede lo stesso comportamento speciale della MOD_1
        #if selected_effect == "EFFECT_3":
#            value = self._scale_value(value, 64, 38)

        if self.last_sent[selected_effect] != value:
            msg = mido.Message("control_change", control=cc_number, value=value)
            self.outport.send(msg)
            self.last_sent[selected_effect] = value
            print(f"[MOD_2] Sent CC {cc_number} with value {value}")
            
    def initialize_effect(self, selected_effect):
        pass
        
    def reset_all(self):
        if not self.outport:
            return
    
        reset_sequences = {
            20: [127, 0],   # EFFECT_1 wet -> reset a 0
            21: [127, 0],   # EFFECT_2 wet -> reset a 0
            22: [127, 0]    # EFFECT_3 rate -> reset al valore base
        }
    
        for cc_number, values in reset_sequences.items():
            for value in values:
                msg = mido.Message("control_change", control=cc_number, value=value)
                self.outport.send(msg)
    
        self.last_sent = {
            "EFFECT_1": 0,
            "EFFECT_2": 0,
            "EFFECT_3": 64
        }
    
        print("[MOD_2] All effects reset")