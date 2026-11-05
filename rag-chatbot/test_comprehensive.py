"""Comprehensive test: 20 sessions x 25 messages each. Reports results by category."""
import json, time, threading, sys, os
from urllib.request import Request, urlopen
from urllib.error import URLError
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URL = "http://localhost:8003/chat"
RESULTS = {}  # session_id -> list of {q, answer, follow_up, suggestions, latency}
LOCK = threading.Lock()

def cleanup_test_data():
    """Delete accumulated test data from DB so each run starts fresh."""
    try:
        import sqlite3
        db = sqlite3.connect("data/sparrowi.db")
        c = db.cursor()
        c.execute("DELETE FROM conversations WHERE session_id LIKE 't0%' OR session_id LIKE 't1%' OR session_id LIKE 't2%'")
        c.execute("DELETE FROM leads WHERE session_id LIKE 't0%' OR session_id LIKE 't1%' OR session_id LIKE 't2%'")
        db.commit()
        db.close()
        print("  [Cleanup] Removed stale test data from database")
    except Exception as e:
        print(f"  [Cleanup] Warning: {e}")

def chat(session_id, message):
    body = json.dumps({"message": message, "session_id": session_id, "page_url": "test"}).encode()
    req = Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        resp = urlopen(req, timeout=20)
        data = json.loads(resp.read())
        latency = round(time.time() - t0, 2)
        return {
            "q": message,
            "answer": data.get("answer", ""),
            "follow_up": data.get("follow_up_message", ""),
            "suggestions": data.get("suggestions", []),
            "latency": latency,
        }
    except Exception as e:
        return {"q": message, "answer": f"ERROR: {e}", "follow_up": "", "suggestions": [], "latency": round(time.time() - t0, 2)}

# ═══════════════════════════════════════════════════════════════════
# 20 TEST SESSIONS — each 25 human-like messages
# ═══════════════════════════════════════════════════════════════════

SESSIONS = {
    # ── 1. General Company Inquiry ──
    "t01_general": [
        "Hi there", "What does your company do?", "okay", "How long have you been around?",
        "That's quite long", "What industries do you serve?", "hmm interesting",
        "Do you work with international clients?", "okay", "What makes you different from others?",
        "sure", "How many projects have you completed?", "wow that's a lot",
        "Can you tell me about your team?", "okay", "Where is your office?",
        "alright", "Do you have a website?", "okay thanks", "How can I reach you?",
        "got it", "Is there a brochure or portfolio I can see?", "okay cool",
        "thanks for the info", "bye",
    ],
    # ── 2. VR/AR Deep Dive ──
    "t02_vrar": [
        "Hello", "I'm looking for VR solutions for my real estate project",
        "What kind of VR do you offer?", "okay", "Do you do AR as well?",
        "Can you give me an example of a VR project you've done?", "nice",
        "How does the virtual walkthrough work?", "interesting",
        "What hardware do you use?", "okay", "Can this work on mobile phones?",
        "hmm", "How long does it take to develop a VR walkthrough?",
        "okay got it", "What about the quality of the visuals?",
        "Can you do a demo for us?", "sure", "What do I need to provide from my end?",
        "alright", "Do you handle the content creation too?", "yes",
        "okay sounds good", "let me discuss with my team", "thanks bye",
    ],
    # ── 3. Interactive Solutions ──
    "t03_interactive": [
        "Hey", "Tell me about interactive solutions", "What is a touch table?",
        "okay", "How does the interactive wall work?", "interesting",
        "Can these be customized for our brand?", "sure",
        "What kind of content can be displayed?", "hmm",
        "Do you also provide the hardware?", "okay",
        "What about maintenance after installation?", "got it",
        "How much space do we need for a touch table?", "alright",
        "Can multiple people use it at the same time?", "nice",
        "Do you have any clients using this in Mumbai?", "okay",
        "Can we visit one of these installations?", "sure that would be great",
        "How do we get started?", "okay I'll get back to you", "thanks",
    ],
    # ── 4. Scale Models ──
    "t04_scalemodels": [
        "Hi", "Do you make scale models?", "What kind of scale models?",
        "okay", "Physical or digital?", "Can you do both?",
        "What materials do you use for physical models?", "hmm",
        "How detailed can you make them?", "okay",
        "Any examples of scale models you've built?", "wow",
        "How long does a typical model take?", "alright",
        "Can we make changes after the model is built?", "okay",
        "Do you deliver or do we pick it up?", "sure",
        "What sizes are available?", "interesting",
        "Can you add lighting to the models?", "nice",
        "Do you do township models?", "okay great",
        "Let me check with my architect", "sure thanks", "bye",
    ],
    # ── 5. Experience Centre Design ──
    "t05_expcentre": [
        "Good morning", "We're building an experience centre for our new township",
        "What do you offer for experience centres?", "okay",
        "Can you design the whole thing end to end?", "That's great",
        "What technology do you typically use?", "hmm",
        "Do you handle the interior design as well?", "interesting",
        "Can you share some experience centres you've built?", "wow impressive",
        "How big should the space be ideally?", "okay",
        "What's the timeline for a complete setup?", "alright",
        "Do you provide training for our sales team?", "sure",
        "What about after-sales support?", "okay",
        "Can you integrate our CRM?", "hmm not sure about that",
        "okay let me think about it", "I'll discuss internally",
        "thanks for your time", "bye",
    ],
    # ── 6. Real Estate Developer Client ──
    "t06_developer": [
        "Hi I'm from a real estate company", "We have a luxury project in Gurgaon",
        "What can you do for luxury real estate?", "okay",
        "We need something that wows our buyers", "What do you suggest?",
        "hmm", "Can you create a virtual tour of our project?",
        "What about a physical model for the sales gallery?", "okay",
        "We also want an interactive price list", "Is that possible?",
        "nice", "How do you handle multiple tower projects?",
        "Can you show different floor plans interactively?", "okay",
        "What about 3D aerial views?", "That sounds good",
        "Do you work with DLF or Godrej type companies?", "okay",
        "We want to start next month", "Can you send us a proposal?",
        "sure", "My name is Rajesh", "thanks I'll share my number later", "bye",
    ],
    # ── 7. Pricing Inquiry (should deflect) ──
    "t07_pricing": [
        "Hello", "I want to know about your services", "okay",
        "How much does a VR walkthrough cost?", "Come on just give me a range",
        "okay", "What about the cost of a scale model?",
        "Even a ballpark figure would help", "hmm",
        "My budget is around 10 lakhs", "okay",
        "Can you do something within that budget?",
        "What's your minimum project size?", "alright",
        "Do you charge per sqft or per project?", "okay",
        "What about payment terms?", "fine",
        "Can I get a written quote?", "sure",
        "Who should I contact for pricing?", "okay",
        "I'll email your team", "okay thanks",
        "bye",
    ],
    # ── 8. Competitor Comparison ──
    "t08_competitor": [
        "Hi", "How are you different from SmartVizX?",
        "okay", "What about compared to Square Yards tech division?",
        "hmm", "Do you have more experience than them?",
        "okay", "What's your USP?", "interesting",
        "Why should we choose you over others?", "sure",
        "Do you have any awards or recognition?", "okay",
        "What about client testimonials?", "nice",
        "How many repeat clients do you have?", "okay",
        "That's a good point", "Can you share case studies?",
        "alright", "Do you have ISO certification?",
        "hmm", "okay I get it", "thanks for explaining", "bye",
    ],
    # ── 9. Career / Hiring Inquiry ──
    "t09_careers": [
        "Hi", "Are you hiring?", "What positions are open?",
        "okay", "Do you have openings for 3D artists?",
        "What about internships?", "hmm",
        "Where is your office located?", "okay",
        "Is it work from home?", "alright",
        "What's the work culture like?", "interesting",
        "How big is your team?", "nice",
        "Do you work with freelancers?", "okay",
        "What software do your artists use?", "hmm",
        "Can I send my portfolio?", "Where should I email?",
        "okay", "Do you hire freshers?", "alright thanks",
        "bye",
    ],
    # ── 10. Office Visit / Location ──
    "t10_location": [
        "Hey there", "Where is your office?", "Is it in Noida?",
        "okay", "How do I get there from Delhi?",
        "Is there a metro nearby?", "hmm",
        "What are your office hours?", "okay",
        "Can I visit for a demo?", "sure",
        "Do I need to book an appointment?", "okay",
        "Can I bring my architect along?", "great",
        "Do you have parking?", "alright",
        "Can we see live projects during the visit?", "nice",
        "How long would a typical demo take?", "okay",
        "Is there a showroom?", "interesting",
        "Can I see the scale models in person?", "okay sounds good",
        "I'll plan a visit next week", "thanks", "bye",
    ],
    # ── 11. Project Portfolio ──
    "t11_portfolio": [
        "Hello", "Can you show me your portfolio?",
        "What are some of your best projects?", "okay",
        "Any projects in Mumbai?", "What about Bangalore?",
        "hmm", "Have you worked on any commercial projects?",
        "okay", "What about hospitality?", "interesting",
        "Tell me about your biggest project", "wow",
        "Do you work on government projects?", "okay",
        "Any international projects?", "nice",
        "How many projects are you currently working on?", "alright",
        "Do you have before and after showcases?", "okay",
        "Can I see videos of your work?", "sure",
        "Where can I find them?", "thanks", "bye",
    ],
    # ── 12. Technical Deep Dive ──
    "t12_technical": [
        "Hi", "What rendering engine do you use?",
        "okay", "What resolution do your VR experiences run at?",
        "Do you use Unreal Engine?", "hmm",
        "What about real-time rendering?", "interesting",
        "Can your solutions run on Oculus Quest?", "okay",
        "What frame rate do you target?", "alright",
        "Do you support 4K displays?", "sure",
        "What about multi-touch support on your tables?", "nice",
        "How many simultaneous touch points?", "okay",
        "Do your interactive walls use projection or LED?", "hmm",
        "What's the typical screen size?", "okay",
        "Do you handle networking for multi-screen setups?", "interesting",
        "okay that's very detailed", "thanks for the technical info", "bye",
    ],
    # ── 13. Casual WhatsApp-Style Chat ──
    "t13_casual": [
        "hii", "how r u", "kya karte ho aap log",
        "acha", "VR wala kaam karte ho?", "hmm",
        "koi example dikhao", "okay", "ye toh accha hai",
        "mere ek project ke liye chahiye", "residential hai",
        "Gurgaon mein", "okay", "kitna time lagega",
        "theek hai", "koi number hai contact ka?",
        "okay", "aur email?", "hmm",
        "main apni team se baat karke batata hun",
        "okay", "accha suno mera naam Amit hai",
        "haan 9876543210", "okay thanks bhai", "bye",
    ],
    # ── 14. Multiple Ack Stress Test ──
    "t14_ack_stress": [
        "What services do you offer?", "okay", "okay", "hmm",
        "Tell me about architectural visualization", "sure", "okay",
        "nice", "got it", "alright",
        "What clients have you worked with?", "okay", "interesting",
        "cool", "hmm", "fine",
        "Do you do 3D rendering?", "okay", "okay",
        "right", "sure", "makes sense",
        "okay", "alright thanks", "bye",
    ],
    # ── 15. End-of-Conversation Patterns ──
    "t15_endconv": [
        "Tell me about Sparrow Interactive", "What do you specialize in?",
        "okay", "Any notable projects?", "interesting",
        "Do you work pan India?", "okay", "hmm",
        "What about after sales service?", "okay got it",
        "I think I have enough information", "nothing more",
        "that's all", "okay", "no more questions",
        "I'm done", "okay", "hmm",
        "actually one more thing", "do you offer annual maintenance contracts?",
        "okay", "that's it then", "alright",
        "thanks for everything", "goodbye",
    ],
    # ── 16. Lead Capture Success Flow ──
    "t16_leadcapture": [
        "Hi", "I'm interested in your services",
        "Tell me about immersive experiences", "okay",
        "Do you do projection mapping?", "nice",
        "Can you handle large venues?", "okay",
        "I have a project coming up in Q2", "It's a luxury township in Noida",
        "We need a full experience centre", "okay",
        "My name is Priya Sharma", "I'm the marketing head",
        "We have about 5000 sqft space", "okay",
        "My number is 9811223344", "sure",
        "priya.sharma@realtycorp.com", "When can we meet?",
        "okay", "I'll be available next Wednesday",
        "thanks Sparrowi", "see you then",
    ],
    # ── 17. Lead Capture Refusal Flow ──
    "t17_leadrefuse": [
        "Hello", "What are your services?", "okay",
        "Tell me about VR walkthroughs", "interesting",
        "Do you customize for each project?", "okay",
        "How realistic are the visuals?", "hmm",
        "Can buyers feel like they're actually there?", "nice",
        "What about furniture and interiors in the VR?", "okay",
        "no I don't want to share my name", "I'm just researching",
        "okay", "I'll contact you when I'm ready",
        "no not now", "maybe later",
        "just tell me your email", "okay got it",
        "I don't want to share my number either", "okay",
        "alright", "thanks bye",
    ],
    # ── 18. Hinglish / Mixed Language ──
    "t18_hinglish": [
        "namaste", "aapki company kya karti hai",
        "achha", "VR mein kya kya milta hai",
        "okay thik hai", "koi real estate project kiya hai kya",
        "hmm", "Godrej ke saath kaam kiya hai?",
        "nice yaar", "aur DLF?", "okay",
        "hum ek naya project launch kar rahe hain",
        "3D model chahiye", "okay",
        "touch table bhi chahiye showroom ke liye",
        "kitne din mein ho jayega", "hmm",
        "theek hai", "mera naam Vikram hai",
        "haan batao kisse baat karni hogi", "okay",
        "number du kya", "9999888877",
        "thanks bhai", "chalo bye",
    ],
    # ── 19. Off-Topic Attempts ──
    "t19_offtopic": [
        "Hi", "What's the weather like today?",
        "okay", "Can you write a poem about buildings?",
        "alright", "What's 245 times 38?",
        "hmm", "Tell me a joke", "okay",
        "Who is the PM of India?", "fine",
        "Can you help me with Python coding?", "okay",
        "Alright then what CAN you help me with?", "Tell me about your services",
        "okay that's better", "Do you have any recent projects?",
        "interesting", "Can you recommend a good architect?",
        "okay", "What about interior designers?",
        "alright", "I understand you only do immersive tech",
        "thanks for clarifying", "bye",
    ],
    # ── 20. Detailed Service Comparison ──
    "t20_comparison": [
        "Hi", "I need help deciding between your services",
        "What's the difference between VR walkthrough and 3D rendering?",
        "okay", "Which one is better for selling apartments?",
        "hmm", "Can I use both together?",
        "interesting", "What about interactive vs immersive?",
        "okay", "Which is more popular among developers?",
        "Do real estate companies prefer physical or digital models?",
        "alright", "What's trending in the market?",
        "Can you suggest what we should go for?", "We have a mid-range residential project",
        "About 200 units", "In Greater Noida",
        "okay", "What combination would work best?",
        "hmm let me think", "Can we start with just VR walkthrough?",
        "and add more later?", "okay that makes sense",
        "thanks for the guidance", "bye",
    ],
}

def run_session(sid, messages):
    results = []
    for msg in messages:
        r = chat(sid, msg)
        results.append(r)
        time.sleep(0.3)  # small gap between messages
    with LOCK:
        RESULTS[sid] = results
    print(f"  ✓ {sid} done ({len(messages)} msgs)")

# ═══════════════════════════════════════════════════════════════════
# RUN TESTS — 5 sessions at a time
# ═══════════════════════════════════════════════════════════════════
def main():
    cleanup_test_data()
    session_ids = list(SESSIONS.keys())
    total = sum(len(m) for m in SESSIONS.values())
    print(f"\n{'='*60}")
    print(f"  COMPREHENSIVE TEST: {len(SESSIONS)} sessions, {total} total messages")
    print(f"{'='*60}\n")

    BATCH_SIZE = 4
    t_start = time.time()

    for i in range(0, len(session_ids), BATCH_SIZE):
        batch = session_ids[i:i+BATCH_SIZE]
        print(f"Batch {i//BATCH_SIZE + 1}: {', '.join(batch)}")
        threads = []
        for sid in batch:
            t = threading.Thread(target=run_session, args=(sid, SESSIONS[sid]))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print()

    elapsed = round(time.time() - t_start, 1)

    # ═══════════════════════════════════════════════════════════════
    # GENERATE REPORT
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  TEST REPORT — {len(RESULTS)} sessions, {total} messages, {elapsed}s total")
    print(f"{'='*70}")

    categories = {
        "General Inquiry": ["t01_general"],
        "Service Deep Dive": ["t02_vrar", "t03_interactive", "t04_scalemodels", "t05_expcentre"],
        "Client Simulation": ["t06_developer", "t13_casual", "t18_hinglish"],
        "Pricing & Competitors": ["t07_pricing", "t08_competitor"],
        "Non-Service Queries": ["t09_careers", "t10_location", "t19_offtopic"],
        "Portfolio & Technical": ["t11_portfolio", "t12_technical", "t20_comparison"],
        "Ack & Conversation Flow": ["t14_ack_stress", "t15_endconv"],
        "Lead Capture": ["t16_leadcapture", "t17_leadrefuse"],
    }

    all_latencies = []
    errors = 0
    ack_responses = []  # track ack/appreciation responses for repetition check
    lead_captures = {"name_asked": 0, "phone_asked": 0, "email_asked": 0}
    farewell_detected = 0
    off_topic_blocked = 0
    pricing_deflected = 0
    specificity_hits = 0  # responses with specific names/projects

    for cat_name, sids in categories.items():
        print(f"\n── {cat_name} ──")
        for sid in sids:
            if sid not in RESULTS:
                print(f"  {sid}: SKIPPED (no results)")
                continue
            msgs = RESULTS[sid]
            errs = sum(1 for m in msgs if m["answer"].startswith("ERROR"))
            lats = [m["latency"] for m in msgs if not m["answer"].startswith("ERROR")]
            avg_lat = round(sum(lats)/len(lats), 2) if lats else 0
            all_latencies.extend(lats)
            errors += errs

            # Analysis
            session_ack_responses = []
            for m in msgs:
                a = m["answer"].lower()
                fu = m["follow_up"].lower() if m["follow_up"] else ""
                q = m["q"].lower().strip()
                combined = a + " " + fu

                # Is this an ack message?
                if q in ["okay", "ok", "hmm", "sure", "alright", "nice", "got it",
                         "interesting", "fine", "cool", "right", "wow", "great",
                         "acha", "achha", "theek hai", "thik hai", "makes sense"]:
                    session_ack_responses.append(m["answer"][:80])
                    ack_responses.append(m["answer"][:80])

                # Lead capture detection
                if any(w in combined for w in ["your name", "what should i call", "may i know your name", "what's your name"]):
                    lead_captures["name_asked"] += 1
                if any(w in combined for w in ["phone number", "contact number", "reach you", "number to"]):
                    lead_captures["phone_asked"] += 1
                if any(w in combined for w in ["email", "e-mail"]):
                    lead_captures["email_asked"] += 1

                # Farewell detection
                if any(w in a for w in ["farewell", "goodbye", "take care", "come back", "great chatting", "pleasure"]):
                    farewell_detected += 1

                # Off-topic blocking
                if any(w in a for w in ["outside my area", "specialize in", "can't help with that", "not something i"]):
                    off_topic_blocked += 1

                # Pricing deflection
                if any(w in a for w in ["tailored to each", "depends on scope", "personalized quote", "project-specific", "custom quote"]):
                    pricing_deflected += 1

                # Specificity (mentions real client/project names)
                if any(w in a for w in ["dlf", "godrej", "m3m", "brigade", "prestige", "jio", "sultan haitham", "sobha"]):
                    specificity_hits += 1

            # Check ack repetition within session
            unique_acks = len(set(session_ack_responses))
            total_acks = len(session_ack_responses)
            ack_variety = f"{unique_acks}/{total_acks} unique" if total_acks > 0 else "N/A"

            label = sid.split("_", 1)[1]
            print(f"  {label:15s} | {len(msgs):2d} msgs | avg {avg_lat:5.2f}s | errs: {errs} | ack variety: {ack_variety}")

    # Overall stats
    avg_all = round(sum(all_latencies)/len(all_latencies), 2) if all_latencies else 0
    max_lat = round(max(all_latencies), 2) if all_latencies else 0
    min_lat = round(min(all_latencies), 2) if all_latencies else 0

    # Global ack repetition
    total_acks = len(ack_responses)
    unique_acks = len(set(ack_responses))

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total messages sent:        {total}")
    print(f"  Errors:                     {errors}")
    print(f"  Avg latency:                {avg_all}s")
    print(f"  Min / Max latency:          {min_lat}s / {max_lat}s")
    print(f"  ")
    print(f"  ── Acknowledgment Handling ──")
    print(f"  Total ack responses:        {total_acks}")
    print(f"  Unique ack responses:       {unique_acks}")
    print(f"  Repetition rate:            {round((1 - unique_acks/total_acks)*100, 1) if total_acks else 0}%")
    print(f"  ")
    print(f"  ── Lead Capture ──")
    print(f"  Name asks detected:         {lead_captures['name_asked']}")
    print(f"  Phone asks detected:        {lead_captures['phone_asked']}")
    print(f"  Email asks detected:        {lead_captures['email_asked']}")
    print(f"  ")
    print(f"  ── Content Quality ──")
    print(f"  Farewell responses:         {farewell_detected}")
    print(f"  Off-topic blocked:          {off_topic_blocked}")
    print(f"  Pricing deflected:          {pricing_deflected}")
    print(f"  Specific names/projects:    {specificity_hits}")
    print(f"  ")
    print(f"  Total time:                 {elapsed}s")
    print(f"{'='*70}")

    # ═══════════════════════════════════════════════════════════════
    # SAMPLE RESPONSES — show 3 example ack exchanges per category
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  SAMPLE ACK/APPRECIATION RESPONSES (showing variety)")
    print(f"{'='*70}")

    sample_sessions = ["t01_general", "t14_ack_stress", "t15_endconv", "t06_developer", "t13_casual"]
    for sid in sample_sessions:
        if sid not in RESULTS:
            continue
        print(f"\n  [{sid}]")
        count = 0
        for m in RESULTS[sid]:
            q = m["q"].lower().strip()
            if q in ["okay", "ok", "hmm", "sure", "alright", "nice", "got it",
                     "interesting", "fine", "cool", "right", "wow", "great",
                     "acha", "achha", "theek hai", "okay thanks", "okay cool",
                     "okay got it", "okay sounds good", "hmm interesting",
                     "that's quite long", "nice yaar"]:
                fu = f" | Follow-up: {m['follow_up'][:60]}" if m["follow_up"] else ""
                print(f"    User: \"{m['q']}\"")
                print(f"    Bot:  {m['answer'][:100]}{fu}")
                count += 1
                if count >= 4:
                    break

    # ═══════════════════════════════════════════════════════════════
    # ISSUES FOUND
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  ISSUES / OBSERVATIONS")
    print(f"{'='*70}")

    issues = []
    if errors > 0:
        issues.append(f"  ⚠ {errors} API errors detected")
    if total_acks > 0 and unique_acks / total_acks < 0.5:
        issues.append(f"  ⚠ High ack repetition rate ({round((1-unique_acks/total_acks)*100)}%) — LLM responses not varied enough")
    if lead_captures["name_asked"] < 5:
        issues.append(f"  ⚠ Low name-ask count ({lead_captures['name_asked']}) — lead capture may not be triggering enough")
    if pricing_deflected < 2:
        issues.append(f"  ⚠ Low pricing deflection count ({pricing_deflected}) — pricing questions may be getting answered")

    # Check for any session where bot repeated exact same ack response 3+ times
    for sid, msgs in RESULTS.items():
        acks = [m["answer"][:60] for m in msgs if m["q"].lower().strip() in
                ["okay", "ok", "hmm", "sure", "alright", "nice", "got it"]]
        from collections import Counter
        c = Counter(acks)
        for resp, cnt in c.items():
            if cnt >= 3:
                issues.append(f"  ⚠ [{sid}] Same ack response repeated {cnt}x: \"{resp[:50]}...\"")

    if not issues:
        print("  ✓ No major issues detected!")
    else:
        for issue in issues:
            print(issue)

    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
