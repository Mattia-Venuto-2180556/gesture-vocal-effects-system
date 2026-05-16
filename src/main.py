import cv2
from gestures import GestureProcessor

mode = "MOD_1"  

if mode == "MOD_1":
    from effects_controls_MOD_1 import EffectsControllerMOD1
elif mode == "MOD_2":
    from effects_controls_MOD_2 import EffectsControllerMOD2

gp = GestureProcessor()

if mode == "MOD_1":
    effects = EffectsControllerMOD1()
elif mode == "MOD_2":
    effects = EffectsControllerMOD2()

# Parametri logic
STABILITY_THRESHOLD = 6
SMOOTHING_FACTOR = 0.1
DEAD_ZONE = 4

# Stato
selected_effect = "NONE"
left_prev_gest = None
left_counter = 0
smoothed_pinch_value = 0

# Double fist reset stability
#double_fist_counter = 0
#DOUBLE_FIST_THRESHOLD = 5

# MOD_2 reset gesture stability
reset_mod2_counter = 0
RESET_MOD2_THRESHOLD = 5


def apply_smoothing(prev, new):
    diff = abs(new - prev)
    if diff < DEAD_ZONE:
        return prev
    alpha = 0.55 if diff > 25 else (0.30 if diff > 12 else SMOOTHING_FACTOR)
    return int(prev * (1 - alpha) + new * alpha)


def apply_smoothing_mod2(prev, new):
    diff = abs(new - prev)

    # Se il movimento è minimo, ignora il jitter
    if diff < 3:
        return prev

    # Se il movimento è ampio, segui subito la mano
    if diff > 25:
        alpha = 0.55

    # Movimento medio: abbastanza reattivo
    elif diff > 10:
        alpha = 0.35

    # Movimento piccolo: più stabile
    else:
        alpha = 0.18

    return int(prev * (1 - alpha) + new * alpha)

def apply_smoothing_mod1(prev, new):
    diff = abs(new - prev)

    if new <= 1:
        return 0
        
    #if new >= 126:
#        return 127

    if diff < DEAD_ZONE:
        return prev

    alpha = 0.65 if diff > 25 else (0.40 if diff > 12 else 0.18)
    return int(prev * (1 - alpha) + new * alpha)


def remap_mod1_output(value):
    OBSERVED_MIN = 0
    OBSERVED_MAX = 122  # valore massimo che stai osservando ora

    value = max(OBSERVED_MIN, min(OBSERVED_MAX, value))

    remapped = int(
        (value - OBSERVED_MIN) / (OBSERVED_MAX - OBSERVED_MIN) * 127
    )

    return max(0, min(127, remapped))

def remap_mod2_output(value):
    OBSERVED_MIN = 1
    OBSERVED_MAX = 117

    value = max(OBSERVED_MIN, min(OBSERVED_MAX, value))

    remapped = int(
        (value - OBSERVED_MIN) / (OBSERVED_MAX - OBSERVED_MIN) * 127
    )

    return max(0, min(127, remapped))


cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results, frame = gp.process_frame(frame)

    # Init variabili UI
    left_gesture = "NO HAND"
    right_gesture = "NO HAND"
    pinch_value = 0
    normalized_value = 0
    right_pinch_distance = None

    left_hand_landmarks = None
    right_hand_landmarks = None

    if results.multi_hand_landmarks:
        # 1. Prima raccolgo le due mani
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            side = handedness.classification[0].label.upper()

            gp.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                gp.mp_hands.HAND_CONNECTIONS
            )

            if side == "LEFT":
                left_hand_landmarks = hand_landmarks
            elif side == "RIGHT":
                right_hand_landmarks = hand_landmarks

        # 2. Calcolo gesture sinistra
        if left_hand_landmarks is not None:
            left_gesture = gp.get_left_gesture_mod1(left_hand_landmarks)

        # 3. Calcolo gesture destra
        if right_hand_landmarks is not None:
            right_fingers = gp.count_fingers(right_hand_landmarks, "RIGHT")
            right_gesture = gp.get_gesture_name(right_fingers)

        # 4. MOD_2 — Double fist reset
        #if mode == "MOD_2" and left_gesture == "FIST" and right_gesture == "FIST":
        # 4. MOD_2 — Double fist reset
#        double_fist_detected = (
#            mode == "MOD_2"
#            and left_hand_landmarks is not None
#            and right_hand_landmarks is not None
#            and left_gesture in ["FIST", "UNKNOWN"]
#            and right_gesture == "FIST"
#            and gp.is_closed_fist(left_hand_landmarks)
#            and gp.is_closed_fist(right_hand_landmarks)
#        )
#
#        if double_fist_detected:
#            double_fist_counter += 1
#        
#            if double_fist_counter >= DOUBLE_FIST_THRESHOLD:
#                effects.reset_all()
#        
#                selected_effect = "NONE"
#                smoothed_pinch_value = 0
#                pinch_value = 0
#                normalized_value = 0
#        
#                left_counter = 0
#                left_prev_gest = None
#        
#                print("[MOD_2] Double fist detected: all effects reset")
#        
#                double_fist_counter = 0
#        
#        else:
#            double_fist_counter = 0

        # 4. MOD_2 — Reset gesture:
        # mano sinistra completamente aperta + pugno destro
        reset_mod2_detected = (
            mode == "MOD_2"
            and left_gesture == "OPEN"
            and right_gesture == "FIST"
        )
        
        if reset_mod2_detected:
            reset_mod2_counter += 1
        
            if reset_mod2_counter >= RESET_MOD2_THRESHOLD:
                effects.reset_all()
        
                selected_effect = "NONE"
                smoothed_pinch_value = 0
                pinch_value = 0
                normalized_value = 0
        
                left_counter = 0
                left_prev_gest = None
        
                print("[MOD_2] Reset gesture detected: all effects reset")
        
                reset_mod2_counter = 0
        
        else:
            reset_mod2_counter = 0
            
            # 5. Logica mano sinistra: selezione effetto
            if left_hand_landmarks is not None:
                if left_gesture == left_prev_gest:
                    left_counter += 1
                else:
                    left_prev_gest, left_counter = left_gesture, 1

                if left_counter >= STABILITY_THRESHOLD:
                    if selected_effect == "NONE":
                        if left_gesture in ["ONE", "TWO", "THREE"]:
                            idx = ["ONE", "TWO", "THREE"].index(left_gesture) + 1
                            selected_effect = f"EFFECT_{idx}"
                            print(f"Selected effect: {selected_effect}")

                            if hasattr(effects, "initialize_effect"):
                                effects.initialize_effect(selected_effect)

                    elif left_gesture in ["FIST", "UNKNOWN"]:
                        selected_effect = "NONE"
                        print(f"Selected effect: {selected_effect}")

                    left_counter = 0

            # 6. Logica mano destra: modulazione
            if right_hand_landmarks is not None:
                if mode == "MOD_1" and right_gesture == "FIST":
                    effects.reset_all()
                    if selected_effect != "NONE":
                        selected_effect = "NONE"
                        print("All effects reset")

                else:
                    if mode == "MOD_1":
                        right_pinch_distance, raw_value, normalized_value = gp.calculate_pinch_data(
                            right_hand_landmarks
                        )

                    elif mode == "MOD_2":
                        right_pinch_distance, raw_value, normalized_value = gp.calculate_hand_openness_data(
                            right_hand_landmarks
                        )

                    if mode == "MOD_1":
                        smoothed_pinch_value = apply_smoothing_mod1(
                            smoothed_pinch_value,
                            raw_value
                        )

                    elif mode == "MOD_2":
                        smoothed_pinch_value = apply_smoothing_mod2(
                            smoothed_pinch_value,
                            raw_value
                        )

                    if mode == "MOD_2":
                        pinch_value = remap_mod2_output(smoothed_pinch_value)
                        if pinch_value <= 1:
                            pinch_value = 0
                    else:
                        #pinch_value = max(0, min(127, smoothed_pinch_value))
                        if mode == "MOD_1":
                            pinch_value = remap_mod1_output(smoothed_pinch_value)
                        #elif mode == "MOD_2":
#                            pinch_value = remap_mod2_output(smoothed_pinch_value)
                    #print(f"raw: {raw_value} | smooth: {smoothed_pinch_value} | sent: {pinch_value}")
                    
                    effects.send_modulation(selected_effect, pinch_value)

    # UI OVERLAY
    cv2.putText(frame, f"Left gesture (effect selection): {left_gesture}", (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    cv2.putText(frame, f"Right gesture (modulation): {right_gesture}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    effect_labels = {
        "EFFECT_1": "EFFECT_1 - REVERB",
        "EFFECT_2": "EFFECT_2 - DELAY",
        "EFFECT_3": "EFFECT_3 - RINGSHIFTER",
        "NONE": "NONE"
    }
    
    display_effect = effect_labels.get(selected_effect, selected_effect)
    
    cv2.putText(frame, f"Selected effect: {display_effect}",
                (10, 120), cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 0, 255), 2)

    cv2.putText(frame, f"Right pinch value: {pinch_value}", (10, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 180, 0), 2)

    cv2.putText(frame, f"Norm: {normalized_value:.2f}", (10, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    if right_pinch_distance is not None:
        cv2.putText(frame, f"Pinch distance: {right_pinch_distance:.3f}", (10, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 0), 2)

    cv2.imshow("Two-Hand Gesture Control System", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()