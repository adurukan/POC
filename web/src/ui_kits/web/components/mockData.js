// Mock data lifted from POC/api/seed.py (first three Turkish questions)
// plus the elevator visual filename mapping.

window.MOCK_QUESTIONS = [
  {
    id: 1,
    subject_name: 'Tam Sayılarla İşlemler',
    question_text:
      'Bir alışveriş merkezinin 3. katında olan Ayşe Hanım asansörle 5 kat aşağıdaki otoparka iniyor. Buna göre otopark alış veriş merkezinin kaçıncı katındadır?',
    solution_steps: [
      { description: 'Ayşe is on the 3rd floor', expression: 'x = 3' },
      { description: 'She goes down 5 floors to the parking lot (y)', expression: 'x − 5 = y' },
      { description: 'Substituting x = 3', expression: 'y = 3 − 5 = −2' },
    ],
    visual_path: 'animated_elevator_scenario.svg',
  },
  {
    id: 2,
    subject_name: 'Tam Sayılarla İşlemler',
    question_text:
      'Sıcaklığı −5°C olan buz, 4°C daha soğutuluyor. Buna göre buzun son durumdaki sıcaklığı kaç °C olur?',
    solution_steps: [
      { description: 'Initial temperature of the ice', expression: 'x = −5' },
      { description: 'It is cooled by 4 more degrees', expression: 'y = x + (−4)' },
      { description: 'Substituting x = −5', expression: 'y = −5 + (−4) = −9' },
    ],
    visual_path: null,
  },
  {
    id: 3,
    subject_name: 'Tam Sayılarla İşlemler',
    question_text:
      "Bir iş merkezinin 20. katında çalışan Rabia, −3. kattaki arşiv odasına gitmek için kaç kat aşağı inmelidir?",
    solution_steps: [
      { description: 'Rabia is on the 20th floor', expression: 'x = 20' },
      { description: 'Archive room is on floor −3', expression: 'y = −3' },
      { description: 'Floors to descend', expression: 'x − y = 20 − (−3) = 23' },
    ],
    visual_path: null,
  },
];

window.MOCK_SUBJECTS = ['Tam Sayılarla İşlemler', 'Cebir', 'Geometri', 'Olasılık'];
