import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

user_states = {}

# --- Centralized Language Responses (with new 'human_escalation' key) ---
responses = {
    'en': {
        'welcome': "Hello! I am your community health assistant. You can:\n1. Check 'symptoms'\n2. 'Register' a child\n3. Ask for a 'vaccine schedule'\n4. Ask for a health 'story'",
        'choose_lang': "Welcome! For English, type 1. हिंदी के लिए 2 दबाएं।",
        'lang_set': "Language set to English.",
        'ask_child_name': "Of course! Let's register a new child. What is the child's name?",
        'ask_dob': "Great. What is {child_name}'s date of birth? Please use DD-MM-YYYY format.",
        'dob_error': "Sorry, that doesn't look like the correct format. Please enter the date of birth as DD-MM-YYYY (e.g., 25-08-2024).",
        'register_success': "Thank you! {child_name} has been registered. You can ask for the 'vaccine schedule'.",
        'no_children': "You haven't registered any children yet. Please send 'register' to add a child first.",
        'symptom_prompt': "Please describe your symptoms in one message (e.g., 'I have a cough and a high fever').",
        'symptom_cold': "Based on your symptoms, it sounds like a common cold. Please get plenty of rest, drink warm fluids, and monitor your temperature. If symptoms worsen, consult a health worker.",
        'symptom_fever': "A fever can be a sign of many things. It's important to rest and stay hydrated. For a high or persistent fever, please seek medical advice.",
        'symptom_unknown': "I'm sorry, I can't diagnose that yet. For any serious symptoms, please see a health worker immediately.",
        'outbreak_alert': "\n\n*⚠️ Community Alert: A high number of fever cases have been reported in your area recently. Please take precautions, wear a mask, and wash your hands frequently.*",
        'health_story': "Today's story is about the Super Soap Team! 🦸‍♂️\n\nImagine tiny, invisible germ villains are trying to make you sick. But you have a secret weapon: the Super Soap Team and their Water-Jetpacks! When you wash your hands, the soap bubbles catch the germ villains, and the water jetpack washes them all away. Washing for 20 seconds is like giving the superheroes enough time to catch all the villains. So, be a hero and wash your hands!",
        'human_escalation': "\n\n*❗Important: Your symptoms may require professional attention. Please contact your local ASHA worker or call the 104 health helpline for advice.*"
    },
    'hi': {
        'welcome': "नमस्ते! मैं आपकी सामुदायिक स्वास्थ्य सहायक हूँ। आप:\n1. 'लक्षण' जांच सकते हैं\n2. बच्चे को 'रजिस्टर' कर सकते हैं\n3. 'टीका शेड्यूल' मांग सकते हैं\n4. स्वास्थ्य 'कहानी' के लिए पूछ सकते हैं",
        'choose_lang': "Welcome! For English, type 1. हिंदी के लिए 2 दबाएं।",
        'lang_set': "भाषा हिंदी में सेट कर दी गई है।",
        'ask_child_name': "बिल्कुल! आइए एक नए बच्चे को पंजीकृत करें। बच्चे का नाम क्या है?",
        'ask_dob': "बहुत अच्छा। {child_name} की जन्म तिथि क्या है? कृपया DD-MM-YYYY प्रारूप का उपयोग करें।",
        'dob_error': "क्षमा करें, यह सही प्रारूप नहीं लगता है। कृपया जन्म तिथि DD-MM-YYYY के रूप में दर्ज करें (उदाहरण: 25-08-2024)।",
        'register_success': "धन्यवाद! {child_name} पंजीकृत हो गया है। आप 'टीका शेड्यूल' के लिए पूछ सकते हैं।",
        'no_children': "आपने अभी तक किसी बच्चे को पंजीकृत नहीं किया है। कृपया पहले एक बच्चे को जोड़ने के लिए 'रजिस्टर' भेजें।",
        'symptom_prompt': "कृपया अपने लक्षण एक संदेश में बताएं (जैसे, 'मुझे खांसी और तेज बुखार है')।",
        'symptom_cold': "आपके लक्षणों के आधार पर, यह सामान्य सर्दी-जुकाम लगता है। कृपया भरपूर आराम करें, गर्म तरल पदार्थ पिएं और अपने तापमान पर नज़र रखें। यदि लक्षण बिगड़ते हैं, तो स्वास्थ्य कार्यकर्ता से सलाह लें।",
        'symptom_fever': "बुखार कई चीजों का संकेत हो सकता है। आराम करना और हाइड्रेटेड रहना महत्वपूर्ण है। तेज या लगातार बुखार के लिए, कृपया चिकित्सकीय सलाह लें।",
        'symptom_unknown': "क्षमा करें, मैं अभी इसका निदान नहीं कर सकता। किसी भी गंभीर लक्षण के लिए, कृपया तुरंत स्वास्थ्य कार्यकर्ता से मिलें।",
        'outbreak_alert': "\n\n*⚠️ सामुदायिक चेतावनी: हाल ही में आपके क्षेत्र में बुखार के कई मामले सामने आए हैं। कृपया सावधानी बरतें, मास्क पहनें और बार-बार हाथ धोएं।*",
        'health_story': "आज की कहानी सुपर सोप टीम के बारे में है! 🦸‍♂️\n\nकल्पना कीजिए कि छोटे, अदृश्य कीटाणु विलेन आपको बीमार करने की कोशिश कर रहे हैं। लेकिन आपके पास एक गुप्त हथियार है: सुपर सोप टीम और उनके वॉटर-जेटपैक! जब आप हाथ धोते हैं, तो साबुन के बुलबुले कीटाणु विलेन को पकड़ लेते हैं, और वॉटर जेटपैक उन सभी को बहा ले जाता है। 20 सेकंड तक हाथ धोना सुपरहीरो को सभी विलेन को पकड़ने के लिए पर्याप्त समय देने जैसा है। तो, हीरो बनें और अपने हाथ धोएं!",
        'human_escalation': "\n\n*❗महत्वपूर्ण: आपके लक्षणों के लिए पेशेवर ध्यान देने की आवश्यकता हो सकती है। कृपया अपनी स्थानीय आशा कार्यकर्ता से संपर्क करें या सलाह के लिए 104 स्वास्थ्य हेल्पलाइन पर कॉल करें।*"
    }
}

# (Database and other helper functions are unchanged)
def add_child_to_db(whatsapp_number, child_name, dob):
    conn = sqlite3.connect('health_db.sqlite')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO children (whatsapp_number, child_name, dob) VALUES (?, ?, ?)",(whatsapp_number, child_name, dob))
    conn.commit()
    conn.close()

def get_children_for_user(whatsapp_number):
    conn = sqlite3.connect('health_db.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT child_name, dob FROM children WHERE whatsapp_number = ?", (whatsapp_number,))
    children = cursor.fetchall()
    conn.close()
    return children

def log_symptoms_to_db(whatsapp_number, symptoms):
    conn = sqlite3.connect('health_db.sqlite')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO symptom_reports (whatsapp_number, reported_symptoms) VALUES (?, ?)", (whatsapp_number, symptoms))
    conn.commit()
    conn.close()

def check_for_outbreak():
    conn = sqlite3.connect('health_db.sqlite')
    cursor = conn.cursor()
    time_24_hours_ago = datetime.now() - timedelta(days=1)
    cursor.execute("""
        SELECT COUNT(*) FROM symptom_reports 
        WHERE (reported_symptoms LIKE '%fever%' OR reported_symptoms LIKE '%बुखार%')
        AND timestamp >= ?
    """, (time_24_hours_ago,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def calculate_vaccine_schedule(dob_str, lang='en'):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    schedule = "Here is a simplified vaccination schedule:\n\n"
    schedule += f"👶 *At Birth* (around {dob.strftime('%d-%b-%Y')}):\n- BCG\n- Oral Polio Vaccine (OPV 0)\n- Hepatitis B (Hep-B 1)\n\n"
    schedule += f"🗓️ *At 6 Weeks* (around {(dob + timedelta(weeks=6)).strftime('%d-%b-%Y')}):\n- DTP 1\n- IPV 1\n- Hepatitis B (Hep-B 2)\n\n"
    schedule += f"🗓️ *At 10 Weeks* (around {(dob + timedelta(weeks=10)).strftime('%d-%b-%Y')}):\n- DTP 2\n- IPV 2\n\n"
    schedule += f"🗓️ *At 14 Weeks* (around {(dob + timedelta(weeks=14)).strftime('%d-%b-%Y')}):\n- DTP 3\n- IPV 3\n"
    schedule += "\n*Note: This is an illustrative schedule. Please consult a healthcare professional for exact dates.*"
    return schedule

# --- Updated symptom_checker to include escalation ---
def symptom_checker(message, lang='en', whatsapp_number=None):
    if whatsapp_number and message:
        log_symptoms_to_db(whatsapp_number, message)
    message = message.lower()
    has_cough = 'cough' in message or 'खांसी' in message or 'khansi' in message
    has_fever = 'fever' in message or 'बुखार' in message or 'bukhar' in message
    has_headache = 'headache' in message or 'सिर दर्द' in message or 'sir dard' in message
    has_runny_nose = 'runny nose' in message or 'stuffy nose' in message
    
    if has_cough and (has_runny_nose or has_headache):
        return responses[lang]['symptom_cold']
    elif has_fever:
        # If fever is detected, add the escalation message
        return responses[lang]['symptom_fever'] + responses[lang]['human_escalation']
    else:
        return responses[lang]['symptom_unknown']

@app.route("/chat", methods=['POST'])
def chat():
    # (This entire function is unchanged from the last version)
    user_message = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    
    if from_number not in user_states:
        user_states[from_number] = {'state': None, 'lang': 'en'}

    current_state = user_states[from_number].get('state')
    user_lang = user_states[from_number].get('lang', 'en')
    
    bot_response_text = ""

    if current_state:
        if current_state == 'awaiting_lang_choice':
            if '1' in user_message:
                user_states[from_number]['lang'] = 'en'
                bot_response_text = responses['en']['lang_set'] + "\n" + responses['en']['welcome']
            elif '2' in user_message:
                user_states[from_number]['lang'] = 'hi'
                bot_response_text = responses['hi']['lang_set'] + "\n" + responses['hi']['welcome']
            else:
                bot_response_text = responses['en']['choose_lang']
                response = MessagingResponse()
                response.message(bot_response_text)
                return str(response)
            user_states[from_number]['state'] = None

        elif current_state == 'awaiting_child_name':
            user_states[from_number]['child_name'] = user_message.title()
            user_states[from_number]['state'] = 'awaiting_dob'
            bot_response_text = responses[user_lang]['ask_dob'].format(child_name=user_message.title())

        elif current_state == 'awaiting_dob':
            try:
                dob_object = datetime.strptime(user_message, '%d-%m-%Y').date()
                child_name = user_states[from_number]['child_name']
                add_child_to_db(from_number, child_name, dob_object)
                bot_response_text = responses[user_lang]['register_success'].format(child_name=child_name)
                user_states[from_number]['state'] = None
                del user_states[from_number]['child_name']
            except ValueError:
                bot_response_text = responses[user_lang]['dob_error']

        elif current_state == 'awaiting_symptoms':
            bot_response_text = symptom_checker(user_message, user_lang, from_number)
            user_states[from_number]['state'] = None
            fever_count = check_for_outbreak()
            OUTBREAK_THRESHOLD = 3
            if fever_count > OUTBREAK_THRESHOLD:
                bot_response_text += responses[user_lang]['outbreak_alert']
    
    else:
        if 'register' in user_message or 'रजिस्टर' in user_message:
            user_states[from_number]['state'] = 'awaiting_child_name'
            bot_response_text = responses[user_lang]['ask_child_name']
        
        elif 'schedule' in user_message or 'शेड्यूल' in user_message:
            children = get_children_for_user(from_number)
            if not children:
                bot_response_text = responses[user_lang]['no_children']
            else:
                full_schedule_text = ""
                for child in children:
                    child_name, dob = child
                    full_schedule_text += f"📅 *Schedule for {child_name}:*\n"
                    full_schedule_text += calculate_vaccine_schedule(dob, user_lang)
                    full_schedule_text += "\n\n"
                bot_response_text = full_schedule_text.strip()

        elif 'symptom' in user_message or 'लक्षण' in user_message:
            user_states[from_number]['state'] = 'awaiting_symptoms'
            bot_response_text = responses[user_lang]['symptom_prompt']
        
        elif 'story' in user_message or 'kahani' in user_message or 'कहानी' in user_message:
            bot_response_text = responses[user_lang]['health_story']

        else:
            user_states[from_number]['state'] = 'awaiting_lang_choice'
            bot_response_text = responses['en']['choose_lang']

    response = MessagingResponse()
    response.message(bot_response_text)
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)