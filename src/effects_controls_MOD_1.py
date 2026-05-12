import mido

class EffectsControllerMOD1:
    def __init__(self, port_name="IAC Driver Bus 1"):
        try:
            self.outport = mido.open_output(port_name)
        except Exception as e:
            print(f"Errore apertura porta MIDI: {e}")
            self.outport = None

        self.EFFECT_CC_MAP = {"EFFECT_1": 20, "EFFECT_2": 21, "EFFECT_3": 22}
        self.last_sent = {"EFFECT_1": None, "EFFECT_2": None, "EFFECT_3": None}

    def _scale_value(self, value, start, end):
        """Helper interno per scalare i valori MIDI."""
        value = max(0, min(127, value))
        scaled = int(start + (value / 127) * (end - start))
        lower, upper = min(start, end), max(start, end)
        return max(lower, min(upper, scaled))

    def send_modulation(self, selected_effect, value):
        if selected_effect == "NONE" or not self.outport:
            return

        cc_number = self.EFFECT_CC_MAP[selected_effect]
        
        # Logica specifica per EFFECT_3 (es. inversione o range ridotto)
#        if selected_effect == "EFFECT_3":
#            value = self._scale_value(value, 64, 38)

        if self.last_sent[selected_effect] != value:
            msg = mido.Message("control_change", control=cc_number, value=value)
            self.outport.send(msg)
            self.last_sent[selected_effect] = value
            print(f"Sent CC {cc_number} with value {value}")

    def reset_all(self):
        if not self.outport:
            return
    
        # Sequenze di reset forzato:
        # invio prima un valore "opposto" e poi il valore di reset,
        # così Logic riceve una variazione reale anche se il parametro
        # è stato modificato manualmente.
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
    
        print("All effects reset")