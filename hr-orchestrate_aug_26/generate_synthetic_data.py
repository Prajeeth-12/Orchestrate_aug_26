import csv
import random
import datetime

# Output file
OUTPUT_FILE = "hr-orchestrate_aug_26/dataset/synthetic_test_data.csv"

# Schemas
COLUMNS = [
    "message_id", "user_id", "conversation_type", "group_id", "business_id", 
    "sender_user_id", "created_at", "message_text", "media_type", "media_id", 
    "forwarded_count", "action", "message_type", "reason", "confidence", "evidence_message_ids"
]

users = [f"u_{str(i).zfill(3)}" for i in range(1, 21)]
groups = [f"group_{str(i).zfill(3)}" for i in range(1, 10)]
businesses = [f"business_{str(i).zfill(3)}" for i in range(1, 10)]

# Scenario Templates
# format: (conv_type, text_template, media_type, fwds, action, msg_type, reason_desc, confidence)

scenarios = [
    # 1. Family Noise (Mute/Digest)
    ("group", "Can someone get milk on the way back? We are totally out.", "", 0, "digest", "personal", "Low-urgency household request", 0.8),
    ("group", "Look at this cute photo of the dog!! 😍🐶", "image", 0, "digest", "personal", "Non-urgent media sharing in family group", 0.85),
    ("group", "Good morning family! Have a blessed day. 🙏", "image", 1, "mute", "greeting", "Generic forwarded morning greeting", 0.95),
    
    # 2. Urgent Personal (Notify)
    ("personal", "Hey I'm outside your house, open the gate pls", "", 0, "notify", "urgent", "Time-sensitive arrival notification", 0.95),
    ("personal", "Dad fell down and we are at City Hospital. Come ASAP.", "", 0, "notify", "urgent", "Critical medical emergency", 0.99),
    ("personal", "Call me NOW.", "", 0, "notify", "urgent", "High urgency personal request", 0.9),
    
    # 3. Work/College Groups (Digest vs Notify)
    ("group", "@all reminder that timesheets are due by 5pm today.", "", 0, "notify", "urgent", "Time-sensitive administrative deadline", 0.85),
    ("group", "Does anyone know if the canteen is serving dosa today?", "", 0, "digest", "personal", "Low priority chatter in college group", 0.8),
    ("group", "Prod is down. @u_005 jump on the bridge immediately.", "", 0, "notify", "urgent", "Critical infrastructure outage alert", 0.95),
    
    # 4. Scams (Mute)
    ("personal", "Congratulations! Your number has won $5,000,000 in the global WhatsApp sweepstakes. Click here to claim.", "", 5, "mute", "scam", "Obvious lottery scam", 0.99),
    ("personal", "Hi mum, I lost my phone and am using a friend's number. Please transfer $500 to this account for my rent.", "", 0, "mute", "scam", "Known 'Hi Mum' impersonation scam", 0.95),
    ("personal", "Dear customer, your electricity connection will be cut at 9:30 PM tonight. Call officer on 9876543210 immediately.", "", 1, "mute", "scam", "Fake utility disconnection scam", 0.92),
    
    # 5. Legitimate Business (Notify/Digest)
    ("business", "Your OTP for login is 482910. Do not share this with anyone.", "", 0, "notify", "urgent", "Time-sensitive authentication code", 0.98),
    ("business", "Your order #8849 has been delivered to your front door.", "", 0, "notify", "business_update", "Important delivery confirmation", 0.9),
    ("business", "BIG SALE! Get 50% off all shoes this weekend only. Shop now!", "image", 0, "digest", "promotion", "Marketing promotion from known brand", 0.88),
    
    # 6. Ambiguous / Difficult cases
    ("personal", "Hey, I need to talk to you about the project. It's urgent.", "", 0, "notify", "urgent", "Direct urgent request", 0.88),
    ("group", "If anyone wants my old couch, I'm giving it away for free today.", "", 0, "digest", "event", "Casual offer in society group", 0.75),
    ("personal", "Can you send me the netflix password again lol", "", 0, "digest", "personal", "Low priority direct message", 0.7),
    ("group", "Pls find the attached voice note for tomorrow's meeting agenda.", "voice", 0, "digest", "business_update", "Non-urgent business voice note", 0.8),
    ("business", "Payment of Rs 1,500 is due tomorrow for your broadband connection.", "", 0, "notify", "payment", "Legitimate upcoming payment reminder", 0.9),
]

def perturb_text(text):
    # Introduce random typos/casual slang for authenticity
    if random.random() < 0.2:
        text = text.replace("you", "u").replace("your", "ur").replace("please", "pls").lower()
    if random.random() < 0.1:
        text = text + " lol"
    if random.random() < 0.1:
        text = text.replace(".", "..")
    return text

def generate_dataset(num_rows=200):
    rows = []
    start_time = datetime.datetime(2026, 8, 1, 8, 0, 0)
    
    for i in range(num_rows):
        scenario = random.choice(scenarios)
        conv_type, text_temp, media, fwds, action, msg_type, reason, conf = scenario
        
        msg_id = f"synth_{str(i+1).zfill(4)}"
        user = random.choice(users)
        
        grp = random.choice(groups) if conv_type == "group" else ""
        bus = random.choice(businesses) if conv_type == "business" else ""
        sender = random.choice(users) if conv_type != "business" else ""
        
        # Ensure sender != user
        while sender == user:
            sender = random.choice(users)
            
        timestamp = start_time + datetime.timedelta(minutes=random.randint(1, 60*24*3))
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        text = perturb_text(text_temp)
        
        # Add some random noise to confidence
        conf_val = min(0.99, max(0.5, conf + random.uniform(-0.05, 0.05)))
        conf_str = f"{conf_val:.2f}"
        
        media_id = ""
        if media == "image":
            media_id = f"img_{str(random.randint(100, 999))}.jpg"
        elif media == "voice":
            media_id = f"vn_{str(random.randint(100, 999))}.mp3"
            
        fwd_count = fwds if random.random() < 0.8 else fwds + random.randint(1, 3)
        if fwds == 0 and random.random() < 0.05:
            fwd_count = 1
            
        ev_id = f"message_{str(random.randint(1000, 9999))}" if random.random() < 0.4 else "none"

        row = [
            msg_id, user, conv_type, grp, bus, sender, ts_str, text, 
            media, media_id, fwd_count, action, msg_type, reason, conf_str, ev_id
        ]
        rows.append(row)
        
    # Sort by timestamp
    rows.sort(key=lambda x: x[6])
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
        
    return len(rows)

if __name__ == "__main__":
    count = generate_dataset(250)
    print(f"Successfully generated {count} authentic synthetic messages at {OUTPUT_FILE}")
