import cv2
import mediapipe as mp
import math

class GestureProcessor:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        # Calibrazione pinch
        self.MIN_PINCH_DISTANCE = 0.035
        self.MAX_PINCH_DISTANCE = 0.27

    def process_frame(self, frame):
        """Converte il frame e processa i landmarks."""
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        return results, frame

    def count_fingers(self, hand_landmarks, hand_side):
        """Conta le dita alzate in base al lato della mano."""
        count = 0
        thumb_tip = hand_landmarks.landmark[4]
        thumb_ip = hand_landmarks.landmark[3]

        if hand_side == "RIGHT":
            if thumb_tip.x < thumb_ip.x: count += 1
        else:
            if thumb_tip.x > thumb_ip.x: count += 1

        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        for tip, pip in zip(finger_tips, finger_pips):
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
                count += 1
        return count

    def get_gesture_name(self, fingers):
        """Mappa il numero di dita al nome della gesture."""
        mapping = {0: "FIST", 1: "ONE", 2: "TWO", 3: "THREE", 5: "OPEN"}
        return mapping.get(fingers, "UNKNOWN")

    def calculate_pinch_data(self, hand_landmarks):
        """
        Calcola il pinch in modo normalizzato rispetto alla dimensione apparente della mano.
        Questo rende la MOD_1 più robusta rispetto alla distanza dalla camera.
        """
    
        thumb = hand_landmarks.landmark[4]
        index = hand_landmarks.landmark[8]
    
        wrist = hand_landmarks.landmark[0]
        middle_mcp = hand_landmarks.landmark[9]
    
        # Scala della mano: distanza polso-base del dito medio
        hand_scale = math.sqrt(
            (middle_mcp.x - wrist.x) ** 2 +
            (middle_mcp.y - wrist.y) ** 2
        )
    
        if hand_scale == 0:
            return 0, 0, 0
    
        # Distanza pinch assoluta
        pinch_dist = math.sqrt(
            (thumb.x - index.x) ** 2 +
            (thumb.y - index.y) ** 2
        )
    
        # Distanza pinch relativa alla dimensione della mano
        pinch_ratio = pinch_dist / hand_scale
    
        # Range da calibrare empiricamente
        MIN_PINCH_RATIO = 0.01
        MAX_PINCH_RATIO = 1.75
    
        norm = (pinch_ratio - MIN_PINCH_RATIO) / (MAX_PINCH_RATIO - MIN_PINCH_RATIO)
        norm = max(0.0, min(1.0, norm))
    
        # Smooth edge
        norm = 3 * (norm ** 2) - 2 * (norm ** 3)
        
        # Soft edge expansion
        norm = 0.5 + (norm - 0.5) * 1.12
        norm = max(0.0, min(1.0, norm))
        
        #if norm < 0.005:
#            norm = 0.0
#        
        if norm > 0.995:
            norm = 1.0
        
        midi_value = int(norm * 127)
            
        print(
            f"pinch_ratio: {pinch_ratio:.3f} | "
            f"norm: {norm:.2f} | midi: {midi_value}"
        )
    
        return pinch_ratio, midi_value, norm

    def is_left_fist_front_facing(self, hand_landmarks):
        """
        Riconosce il FIST sinistro solo quando le dita chiuse sono orientate
        verso la camera. Se la mano è laterale o se le nocche sono rivolte
        verso la camera, il pugno non viene considerato valido.
        """
    
        wrist = hand_landmarks.landmark[0]
    
        # Fingertip delle quattro dita lunghe
        tips = [
            hand_landmarks.landmark[8],   # index
            hand_landmarks.landmark[12],  # middle
            hand_landmarks.landmark[16],  # ring
            hand_landmarks.landmark[20]   # pinky
        ]
    
        # MCP = base delle dita / nocche
        mcps = [
            hand_landmarks.landmark[5],   # index MCP
            hand_landmarks.landmark[9],   # middle MCP
            hand_landmarks.landmark[13],  # ring MCP
            hand_landmarks.landmark[17]   # pinky MCP
        ]
    
        # 1) Le dita devono essere realmente raccolte:
        # le punte devono stare sotto/verso il palmo rispetto alle MCP.
        curled_fingers = 0
        for tip, mcp in zip(tips, mcps):
            if tip.y > mcp.y:
                curled_fingers += 1
    
        fingers_are_curled = curled_fingers >= 3
    
        # 2) Le punte delle dita devono essere più vicine alla camera delle nocche.
        # In MediaPipe, z più negativo = più vicino alla camera.
        avg_tip_z = sum(tip.z for tip in tips) / len(tips)
        avg_mcp_z = sum(mcp.z for mcp in mcps) / len(mcps)
    
        fingertips_face_camera = avg_tip_z < avg_mcp_z - 0.015
    
        # 3) La mano non deve essere troppo laterale:
        # se la larghezza MCP è troppo piccola, probabilmente la mano è di profilo.
        index_mcp = hand_landmarks.landmark[5]
        pinky_mcp = hand_landmarks.landmark[17]
        middle_mcp = hand_landmarks.landmark[9]
    
        hand_width = abs(index_mcp.x - pinky_mcp.x)
        hand_height = abs(wrist.y - middle_mcp.y)
    
        if hand_height == 0:
            return False
    
        width_height_ratio = hand_width / hand_height
        not_sideways = width_height_ratio > 0.45
    
        return fingers_are_curled and fingertips_face_camera and not_sideways
        
    def get_left_gesture_mod1(self, hand_landmarks):
        """
        Gesture mano sinistra MOD_1.
        Se le quattro dita lunghe sono chiuse, la gesture può essere solo:
        - FIST, se front-facing valido
        - UNKNOWN, se laterale o con nocche verso camera
        Mai ONE/TWO/THREE.
        """
    
        wrist = hand_landmarks.landmark[0]
    
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
    
        long_fingers_extended = 0
    
        for tip_id, pip_id in zip(finger_tips, finger_pips):
            tip = hand_landmarks.landmark[tip_id]
            pip = hand_landmarks.landmark[pip_id]
    
            if tip.y < pip.y:
                long_fingers_extended += 1
    
        # Caso pugno / dita lunghe chiuse:
        # qui il pollice NON deve mai generare ONE.
        if long_fingers_extended == 0:
            if self.is_left_fist_front_facing(hand_landmarks):
                return "FIST"
            else:
                return "UNKNOWN"
    
        # Solo se almeno un dito lungo è davvero esteso,
        # allora uso il conteggio standard.
        fingers = self.count_fingers(hand_landmarks, "LEFT")
        return self.get_gesture_name(fingers)
    
    def calculate_hand_openness_data(self, hand_landmarks):
        """
        Calcola l'apertura della mano in modo normalizzato rispetto
        alla dimensione apparente della mano.
        0   = pugno chiuso
        127 = mano aperta
        """
    
        wrist = hand_landmarks.landmark[0]
        middle_mcp = hand_landmarks.landmark[9]
    
        # Scala della mano: distanza polso-base del dito medio
        hand_scale = math.sqrt(
            (middle_mcp.x - wrist.x) ** 2 +
            (middle_mcp.y - wrist.y) ** 2
        )
    
        if hand_scale == 0:
            return 0, 0, 0
    
        finger_tips = [8, 12, 16, 20]
        distances = []
    
        for tip_id in finger_tips:
            tip = hand_landmarks.landmark[tip_id]
    
            dist = math.sqrt(
                (tip.x - wrist.x) ** 2 +
                (tip.y - wrist.y) ** 2
            )
    
            # distanza relativa, non assoluta
            distances.append(dist / hand_scale)
    
        #openness_ratio = max(distances)
        #openness_ratio = sum(distances) / len(distances)
        openness_ratio = (
            0.7 * (sum(distances) / len(distances))
            + 0.3 * max(distances)
        )
    
        # Range relativo, molto meno sensibile alla distanza dalla camera
        #MIN_OPENNESS = 1.10
        #MAX_OPENNESS = 1.90
        
        MIN_OPENNESS = 1.00
        MAX_OPENNESS = 1.90
    
        norm = (openness_ratio - MIN_OPENNESS) / (MAX_OPENNESS - MIN_OPENNESS)
        norm = max(0.0, min(1.0, norm))
    
#        if norm < 0.08:
#            norm = 0.0
#        if norm > 0.92:
#            norm = 1.0
            
        fingers = self.count_fingers(hand_landmarks, "RIGHT")
        if fingers == 0:
            return openness_ratio, 0, 0.0
    
        # Smooth transition
        norm = 3 * (norm ** 2) - 2 * (norm ** 3)
        
        # Curva più progressiva: rallenta la salita
        norm = norm ** 1.25
        
        # Edge expansion morbida ma più efficace
        norm = 0.5 + (norm - 0.5) * 1.05
        norm = max(0.0, min(1.0, norm))
        
        midi_value = int(norm * 127)
        
        norm = max(0.0, min(1.0, norm))
        
        midi_value = int(norm * 127)
        #response_curve = norm ** 2.0
        #midi_value = int(response_curve * 127)
    
#        print(
#            f"openness_ratio: {openness_ratio:.3f} | "
#            f"norm: {norm:.2f} | midi: {midi_value}"
#        )
        
        print(
            f"openness_ratio: {openness_ratio:.3f} | "
            f"norm: {norm:.2f} | "
            f"midi: {midi_value}"
        )
    
        return openness_ratio, midi_value, norm
    
    def _distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
     
    def is_closed_fist(self, hand_landmarks):
        """
        Rileva un pugno chiuso ignorando il pollice.
        Usato per il double fist reset in MOD_2.
        """
    
        wrist = hand_landmarks.landmark[0]
    
        finger_data = [
            (8, 6, 5),      # index: tip, pip, mcp
            (12, 10, 9),    # middle
            (16, 14, 13),   # ring
            (20, 18, 17)    # pinky
        ]
    
        closed_count = 0
    
        for tip_id, pip_id, mcp_id in finger_data:
            tip = hand_landmarks.landmark[tip_id]
            pip = hand_landmarks.landmark[pip_id]
            mcp = hand_landmarks.landmark[mcp_id]
    
            tip_to_wrist = self._distance(tip, wrist)
            pip_to_wrist = self._distance(pip, wrist)
            mcp_to_wrist = self._distance(mcp, wrist)
    
            # Dito chiuso se la punta non è molto più lontana dal polso rispetto alle articolazioni
            if tip_to_wrist < pip_to_wrist * 1.12:
                closed_count += 1
    
        return closed_count >= 3