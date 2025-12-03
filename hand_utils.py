def count_fingers(hand_landmarks):
    fingers = []
    # thumb
    if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
        fingers.append(1)
    else:
        fingers.append(0)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for i in range(4):
        if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y:
            fingers.append(1)
        else:
            fingers.append(0)
    return sum(fingers)


def palm_openness(hand_landmarks):
    wrist = hand_landmarks.landmark[0]
    tips = [4, 8, 12, 16, 20]
    dists = []
    for t in tips:
        lm = hand_landmarks.landmark[t]
        dx = lm.x - wrist.x
        dy = lm.y - wrist.y
        d = (dx * dx + dy * dy) ** 0.5
        dists.append(d)
    avg = sum(dists) / len(dists)
    min_dist = 0.03
    max_dist = 0.22
    openness = (avg - min_dist) / (max_dist - min_dist)
    if openness < 0:
        openness = 0.0
    if openness > 1:
        openness = 1.0
    return openness


def fingertip_distance(hand_landmarks, idx1=4, idx2=8):
    a = hand_landmarks.landmark[idx1]
    b = hand_landmarks.landmark[idx2]
    dx = a.x - b.x
    dy = a.y - b.y
    return (dx * dx + dy * dy) ** 0.5
