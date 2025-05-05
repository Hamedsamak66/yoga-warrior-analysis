import cv2
import numpy as np
import mediapipe as mp
import csv
import winsound

# مسیر ویدیو ورودی و خروجی
input_path = "1.mp4"  # ویدیوی ورودی
output_path = "warrior_full_analysis_v3.mp4"  # ویدیوی خروجی با نام متفاوت

# محدوده‌های مجاز زاویه برای Warrior II
angle_ranges = {
    "Right Knee": (80, 110),      # زانوی جلو باید بین 80 تا 110 درجه خم شود
    "Right Hip": (80, 100),       # لگن باید با زانو هم‌راستا باشد
    "Right Arm": (80, 110),       # بازو باید موازی با زمین باشد
    "Left Knee": (165, 180),      # پای عقب باید صاف باشد
    "Left Hip": (120, 180),       # لگن پای عقب باید صاف باشد
    "Left Arm": (80, 100)         # بازوی چپ هم باید موازی با زمین باشد
}

# راه‌اندازی MediaPipe Pose با حساسیت بیشتر
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.7,    # افزایش دقت تشخیص
    min_tracking_confidence=0.7,     # افزایش دقت ردیابی
    model_complexity=2              # استفاده از مدل پیچیده‌تر برای دقت بیشتر
)
mp_drawing = mp.solutions.drawing_utils

# ایجاد فایل CSV برای ذخیره زوایا
with open("angles_log_v3.csv", "w", newline="") as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["Frame", "Right Knee", "Right Hip", "Right Arm", 
                       "Left Knee", "Left Hip", "Left Arm", "Status"])

cap = cv2.VideoCapture(input_path)
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(3))
height = int(cap.get(4))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

def calc_angle(a, b, c):
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
    return angle

frame_idx = 0
last_warning = 0  # برای کنترل فاصله زمانی بین هشدارها

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # اضافه کردن عنوان در بالای صفحه با فونت زیبا
    title = "Yoga Warrior II Pose Analysis"
    # ایجاد یک پس‌زمینه مستطیلی برای عنوان
    title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_COMPLEX, 1.2, 2)[0]
    title_x = (width - title_size[0]) // 2  # مرکز افقی
    cv2.rectangle(frame, 
                 (title_x - 10, 5), 
                 (title_x + title_size[0] + 10, 45), 
                 (255, 255, 255), 
                 -1)  # پس‌زمینه سفید
    cv2.putText(frame, 
                title,
                (title_x, 35),  # موقعیت متن
                cv2.FONT_HERSHEY_COMPLEX,  # فونت زیبا
                1.2,  # اندازه فونت
                (0, 0, 0),  # رنگ مشکی
                2,  # ضخامت
                cv2.LINE_AA)  # آنتی‌آلیاسینگ برای نمایش بهتر

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    detected_angles = {}
    in_range_flags = {}

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark
        get = lambda i: np.array([lm[i].x * width, lm[i].y * height])
        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # رسم نقاط کلیدی با شماره
        for i, landmark in enumerate(result.pose_landmarks.landmark):
            x, y = int(landmark.x * width), int(landmark.y * height)
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
            cv2.putText(frame, str(i), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        try:
            # محاسبه صحیح زوایا با ترتیب درست نقاط
            right_knee_angle = calc_angle(get(24), get(26), get(28))  # ران ← زانو ← مچ (اصلاح شده)
            right_hip_angle = calc_angle(get(12), get(24), get(26))   # شانه ← ران ← زانو (درست است)
            right_arm_angle = calc_angle(get(14), get(12), get(24))   # آرنج ← شانه ← ران
            
            left_knee_angle = calc_angle(get(23), get(25), get(27))   # ران ← زانو ← مچ (درست است)
            left_hip_angle = calc_angle(get(11), get(23), get(25))    # شانه ← ران ← زانو
            left_arm_angle = calc_angle(get(13), get(11), get(23))    # آرنج ← شانه ← ران (درست است)

            detected_angles = {
                "Right Knee": (right_knee_angle, get(26)),
                "Right Hip": (right_hip_angle, get(24)),
                "Right Arm": (right_arm_angle, get(12)),
                "Left Knee": (left_knee_angle, get(25)),
                "Left Hip": (left_hip_angle, get(23)),
                "Left Arm": (left_arm_angle, get(11))
            }

            for k, (angle, _) in detected_angles.items():
                min_val, max_val = angle_ranges[k]
                in_range_flags[k] = min_val <= angle <= max_val

            # ذخیره در CSV
            status = "Correct" if all(in_range_flags.values()) else "Incorrect"
            with open("angles_log_v3.csv", "a", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([
                    frame_idx,
                    right_knee_angle,
                    right_hip_angle,
                    right_arm_angle,
                    left_knee_angle,
                    left_hip_angle,
                    left_arm_angle,
                    status
                ])

        except Exception as e:
            print(f"Error in frame {frame_idx}: {e}")

    # نمایش اطلاعات روی تصویر
    y_pos = 40
    all_good = all(in_range_flags.values()) if in_range_flags else False
    
    # نمایش محدوده‌های مجاز با رنگ مشکی
    cv2.putText(frame, "Allowed Ranges:", (width-200, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y = 50
    for k, (min_val, max_val) in angle_ranges.items():
        cv2.putText(frame, f"{k}: {min_val}-{max_val}", (width-200, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        y += 20

    for label, (angle, pos) in detected_angles.items():
        color = (0, 255, 0) if in_range_flags[label] else (0, 0, 255)
        
        # نمایش زاویه در گوشه
        cv2.putText(frame, f"{label}: {int(angle)} deg", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        y_pos += 35

        # نمایش زاویه روی مفصل
        cv2.putText(frame, f"{int(angle)} deg", tuple(pos.astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    if all_good:
        cv2.putText(frame, " Correct Warrior II Pose", (50, height-50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    else:
        cv2.putText(frame, " Incorrect Pose", (50, height-50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        # هشدار صوتی با فاصله زمانی
        if frame_idx - last_warning > fps * 2:  # هر 2 ثانیه
            winsound.Beep(1000, 200)
            last_warning = frame_idx

    # شماره فریم
    cv2.putText(frame, f"Frame: {frame_idx}", (20, height-20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # اضافه کردن لینک لینکدین
    cv2.putText(
        frame,
        "linkedin.com/in/hamedsamak",
        (frame.shape[1] - 460, frame.shape[0] - 20),
        cv2.FONT_HERSHEY_DUPLEX,
        0.9,
        (0, 255, 255),  # رنگ زرد
        2,
        cv2.LINE_AA
    )

    out.write(frame)
    frame_idx += 1

cap.release()
out.release()
print(f"✅ Analysis complete! Output saved as: {output_path}")
print(f"✅ Angle data saved in: angles_log_v3.csv")