from database import SessionLocal
from models.question import Question

questions = [
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Bir alışveriş merkezinin 3. katında olan Ayşe Hanım asansörle "
            "5 kat aşağıdaki otoparka iniyor. Buna göre otopark alış veriş "
            "merkezinin kaçıncı katındadır?"
        ),
        "solution_steps": [
            {"description": "Ayşe is on the 3rd floor", "expression": "x = 3"},
            {"description": "She goes down 5 floors to the parking lot (y)", "expression": "x - 5 = y"},
            {"description": "Substituting x = 3", "expression": "y = 3 - 5 = -2"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Sıcaklığı -5°C olan buz, 4°C daha soğutuluyor. "
            "Buna göre buzun son durumdaki sıcaklığı kaç °C olur?"
        ),
        "solution_steps": [
            {"description": "Initial temperature of the ice", "expression": "x = -5"},
            {"description": "It is cooled by 4 more degrees", "expression": "y = x + (-4)"},
            {"description": "Substituting x = -5", "expression": "y = -5 + (-4) = -9"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Bir iş merkezinin 20. katında çalışan Rabia, -3. kattaki arşiv "
            "odasına gitmek için kaç kat aşağı inmelidir?"
        ),
        "solution_steps": [
            {"description": "Rabia is on the 20th floor", "expression": "x = 20"},
            {"description": "Archive room is on floor -3", "expression": "y = -3"},
            {"description": "Floors to descend", "expression": "x - y = 20 - (-3) = 20 + 3 = 23"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Ankara'da gece sıcaklığı -3°C, gündüz sıcaklığı +8°C olduğuna göre, "
            "gece ve gündüz arasındaki sıcaklık farkını bulunuz."
        ),
        "solution_steps": [
            {"description": "Night temperature", "expression": "x = -3"},
            {"description": "Day temperature", "expression": "y = 8"},
            {"description": "Temperature difference", "expression": "y - x = 8 - (-3) = 8 + 3 = 11"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Bir dalgıç, deniz seviyesinden 100 m derinliğe dalıyor. Sonra 40 m "
            "yukarı çıkıyor. Sonra tekrar 15 m derinliğe dalıyor. Buna göre "
            "dalgıcın son andaki konumunu yazınız."
        ),
        "solution_steps": [
            {"description": "Diver goes 100m below sea level", "expression": "x = -100"},
            {"description": "Rises 40m upward", "expression": "-100 + 40 = -60"},
            {"description": "Dives 15m deeper", "expression": "-60 - 15 = -75"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "20 soruluk bir deneme sınavında tüm soruları cevaplayan Arda, her doğru "
            "cevap için (+5) puan, her yanlış cevap için (-3) puan alacaktır. "
            "16 soruyu doğru cevaplayan Arda kaç puan alır?"
        ),
        "solution_steps": [
            {"description": "Wrong answers: 20 - 16 = 4", "expression": "20 - 16 = 4"},
            {"description": "Points from correct answers", "expression": "16 × 5 = 80"},
            {"description": "Points from wrong answers", "expression": "4 × (-3) = -12"},
            {"description": "Total score", "expression": "80 + (-12) = 68"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Sıcaklığı 12°C olan bir ürün buzdolabına konulduğunda sıcaklığı her bir "
            "saatte 3°C azalmaktadır. Buna göre buzdolabındaki bu ürünün 6 saat "
            "sonraki sıcaklığı kaç °C olur?"
        ),
        "solution_steps": [
            {"description": "Initial temperature", "expression": "x = 12"},
            {"description": "Total drop over 6 hours", "expression": "6 × (-3) = -18"},
            {"description": "Temperature after 6 hours", "expression": "12 + (-18) = -6"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Hafta içi her gün 6 TL harçlık alan Ahmet hafta sonu her gün 3 TL "
            "harcadığına göre 4 hafta sonunda elinde ne kadar parası olur?"
        ),
        "solution_steps": [
            {"description": "Weekday income: 5 days × 6 TL", "expression": "5 × 6 = 30"},
            {"description": "Weekend spending: 2 days × 3 TL", "expression": "2 × (-3) = -6"},
            {"description": "Net gain per week", "expression": "30 + (-6) = 24"},
            {"description": "Total after 4 weeks", "expression": "4 × 24 = 96"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Sınıfa 50 tane ceviz getiren Suat Öğretmen kızlara ikişer erkeklere de "
            "üçer ceviz dağıtmış birini de kendisine saklamıştır. 11 kız öğrencinin "
            "olduğu bu sınıftaki erkek öğrenci sayısı kaçtır?"
        ),
        "solution_steps": [
            {"description": "Walnuts given to 11 girls at 2 each", "expression": "11 × 2 = 22"},
            {"description": "Walnuts accounted for (girls + teacher)", "expression": "22 + 1 = 23"},
            {"description": "Remaining for boys", "expression": "50 - 23 = 27"},
            {"description": "Number of boys (3 each)", "expression": "27 ÷ 3 = 9"},
        ],
        "visual_path": None,
    },
    {
        "subject_name": "Tam Sayılarla İşlemler",
        "question_text": (
            "Bir fırının sıcaklığı, her 3 dakikada 4°C artmaktadır. Başlangıçta "
            "25°C olan bir fırın kaç dakika sonra 85°C sıcaklığa ulaşır?"
        ),
        "solution_steps": [
            {"description": "Temperature rise needed", "expression": "85 - 25 = 60"},
            {"description": "Number of 3-minute intervals needed", "expression": "60 ÷ 4 = 15"},
            {"description": "Total time in minutes", "expression": "15 × 3 = 45"},
        ],
        "visual_path": None,
    },
]

db = SessionLocal()
for q in questions:
    db.add(Question(**q))
db.commit()
db.close()

print(f"Inserted {len(questions)} questions.")
