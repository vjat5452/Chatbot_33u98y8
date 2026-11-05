"""Lead detection, scoring, and intent classification for the sales bot layer."""

import re
from collections import Counter

# ── Contact info extraction patterns ──

_EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.\w{2,}')
_FAKE_DOMAINS = {"fake", "test", "example", "invalid", "localhost", "asdf", "xxx"}


def _is_valid_email(email: str) -> bool:
    """Strict email validation — rejects double @, short TLDs, disposable patterns, etc."""
    if email.count("@") != 1:
        return False
    local, domain = email.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        return False
    # Reject very short or suspicious domains
    domain_parts = domain.split(".")
    if len(domain_parts) < 2 or any(len(p) < 2 for p in domain_parts):
        return False
    # TLD must be at least 2 chars and only alpha
    tld = domain_parts[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False
    # Domain name (before TLD) must be at least 2 chars
    if len(domain_parts[-2]) < 2:
        return False
    # Reject if local part has consecutive dots or starts/ends with dot
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    # Local part must have at least 1 alphanumeric character
    if not any(c.isalnum() for c in local):
        return False
    # Reject obvious test/fake patterns
    if domain_parts[-2].lower() in _FAKE_DOMAINS:
        return False
    # Reject if domain has no valid DNS-style structure (only alphanumeric + hyphens)
    for part in domain_parts:
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', part):
            return False
    return True

_PHONE_PATTERNS = [
    # International 4-group: +44-20-7946-0958, +61-2-9876-5432
    r'\+\d{1,3}[-.\s]\d{1,4}[-.\s]\d{3,4}[-.\s]\d{3,4}',
    # International 3-group: +968-2345-6789
    r'\+\d{1,3}[-.\s]\d{3,5}[-.\s]\d{3,5}',
    # International 2-group with long local: +971-50-1234567
    r'\+\d{1,3}[-.\s]\d{1,4}[-.\s]\d{5,8}',
    # Indian mobile 5+5 with +91: +91 99100 88877
    r'\+91[-.\s]?\d{5}[-.\s]\d{5}',
    # Indian landline: 011-4567-8900, 022-2345-6789
    r'0\d{2,3}[-.\s]?\d{4}[-.\s]?\d{4}',
    # Standard 10-digit: (xxx) xxx-xxxx, xxx-xxx-xxxx, +x-xxx-xxx-xxxx
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    # Bare 10-digit number (Indian mobile): 9876543210
    r'\b[6-9]\d{9}\b',
]
_PHONE_RE = re.compile('|'.join(_PHONE_PATTERNS))


def _is_valid_phone(phone: str) -> bool:
    """Reject obviously fake phone numbers."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 7:
        return False
    # Reject too-long numbers (max 13 digits: country code + 10-digit number)
    if len(digits) > 13:
        return False
    # Reject all same digit (e.g., 1111111111)
    if len(set(digits)) == 1:
        return False
    # Reject purely sequential ascending/descending (e.g., 1234567890, 0987654321)
    # Check if each consecutive digit differs by exactly +1 or -1
    _is_ascending = all(int(digits[i+1]) - int(digits[i]) == 1 or
                        (digits[i] == '9' and digits[i+1] == '0')
                        for i in range(len(digits)-1))
    _is_descending = all(int(digits[i]) - int(digits[i+1]) == 1 or
                         (digits[i] == '0' and digits[i+1] == '9')
                         for i in range(len(digits)-1))
    if _is_ascending or _is_descending:
        return False
    # Reject numbers with excessive digit repetition (e.g., 98076543377777)
    most_common_count = Counter(digits).most_common(1)[0][1]
    if most_common_count > len(digits) * 0.5:
        return False
    return True

_NAME_PATTERNS = re.compile(
    r"(?:"
    r"(?:[Ii]'?m|[Mm]y\s+name\s+is|[Nn]ame\s+is|[Tt]his\s+is|[Ii]\s+am|[Cc]all\s+me)\s+"
    r"([A-Z][a-z]{1,}(?:\s+[A-Za-z][a-z]+){0,2})"   # Group 1: name after intro phrase
    r"|"
    r"(?:[Ii]t'?s\s+)"                                # "It's Rahul here"
    r"([A-Z][a-z]{1,}(?:\s+[A-Za-z][a-z]+){0,2})"   # Group 2: name after "it's"
    r"(?:\s+(?:here|speaking))?"
    r"|"
    r"^([A-Z][a-z]{1,}(?:\s+[A-Za-z][a-z]+){0,2})"  # Group 3: name at start
    r"\s+(?:here|speaking|from\s+\w+)"                # REQUIRED suffix for bare start-of-message
    r"|"
    # Group 4: "<name> is what you can call me" / "<name> is my name"
    r"([A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){0,2})"
    r"\s+(?:is\s+(?:what\s+you\s+can\s+call\s+me|my\s+name|the\s+name)|you\s+can\s+call\s+me)"
    r"|"
    # Group 5: Hindi — "mera naam Rohit hai" / "mera naam Rohit"
    r"(?:[Mm]era\s+naam\s+)"
    r"([A-Za-z][a-z]{1,}(?:\s+[A-Za-z][a-z]+){0,2})"
    r"(?:\s+hai)?"  # optional trailing "hai" (Hindi "is") — NOT captured
    r"|"
    # Group 6: mid-message "X here" — "so Arjun here", ", Priya here"
    r"(?:,\s*(?:so\s+)?|(?:and|so)\s+)"
    r"([A-Z][a-z]{1,}(?:\s+[A-Za-z][a-z]+){0,2})"
    r"\s+here\b"
    r")"
)

# Phrases that indicate the bot just asked for the visitor's name
# ── Name validation: reject common English words that aren't real names ──
_NOT_A_NAME_WORDS = {
    # Common verbs
    "alone", "run", "walk", "talk", "think", "know", "want", "need", "like",
    "love", "hate", "make", "take", "give", "find", "tell", "ask", "try",
    "come", "go", "see", "look", "use", "work", "call", "play", "move",
    "live", "believe", "bring", "happen", "write", "sit", "stand", "lose",
    "pay", "meet", "include", "continue", "set", "learn", "change", "lead",
    "understand", "watch", "follow", "stop", "create", "speak", "read",
    "spend", "grow", "open", "walk", "win", "teach", "offer", "remember",
    "consider", "appear", "buy", "wait", "serve", "die", "send", "build",
    "stay", "fall", "cut", "reach", "kill", "remain", "suggest", "raise",
    "pass", "sell", "require", "report", "decide", "pull", "develop",
    "sleep", "eat", "drink", "sing", "dance", "jump", "swim", "fight",
    "drive", "fly", "ride", "hide", "seek", "break", "choose", "forgot",
    "running", "walking", "talking", "thinking", "working", "playing",
    "coming", "going", "looking", "doing", "saying", "getting", "making",
    # Common adjectives
    "good", "bad", "big", "small", "great", "large", "long", "short",
    "old", "young", "new", "first", "last", "high", "low", "right",
    "wrong", "best", "worst", "important", "different", "same", "early",
    "late", "possible", "impossible", "real", "fake", "free", "full",
    "empty", "hot", "cold", "warm", "cool", "fast", "slow", "hard",
    "soft", "strong", "weak", "rich", "poor", "happy", "sad", "angry",
    "beautiful", "ugly", "smart", "stupid", "clever", "brave", "lazy",
    "busy", "quiet", "loud", "dark", "light", "clean", "dirty", "safe",
    "dangerous", "healthy", "sick", "simple", "complex", "easy", "difficult",
    "cheap", "expensive", "pretty", "handsome", "tall", "thin", "thick",
    "heavy", "bright", "dull", "sharp", "smooth", "rough", "wet", "dry",
    "fresh", "sweet", "bitter", "sour", "spicy", "gentle", "rough",
    # Common adverbs
    "very", "really", "always", "never", "often", "sometimes", "usually",
    "just", "also", "still", "already", "again", "here", "there", "now",
    "then", "today", "tomorrow", "yesterday", "soon", "quickly", "slowly",
    "well", "badly", "almost", "quite", "enough", "too", "much", "more",
    "less", "only", "even", "ever", "perhaps", "maybe", "probably",
    "actually", "basically", "literally", "seriously", "honestly",
    "together", "apart", "alone", "away", "inside", "outside", "above",
    "below", "ahead", "behind", "forever", "absolutely", "definitely",
    # Common nouns (non-name)
    "thing", "time", "year", "people", "way", "day", "man", "woman",
    "child", "world", "life", "hand", "part", "place", "case", "week",
    "company", "system", "program", "question", "work", "government",
    "number", "night", "point", "home", "water", "room", "mother",
    "father", "area", "money", "story", "fact", "month", "lot", "study",
    "book", "eye", "job", "word", "business", "issue", "side", "kind",
    "head", "house", "service", "friend", "power", "hour", "game",
    "line", "end", "member", "city", "student", "class", "food",
    "country", "car", "body", "dog", "cat", "bird", "fish", "tree",
    "flower", "music", "movie", "school", "office", "table", "chair",
    "phone", "computer", "website", "internet", "email", "nothing",
    "something", "everything", "anything", "nobody", "somebody",
    "everyone", "anyone", "myself", "yourself", "himself", "herself",
    # Pronouns / determiners / prepositions / conjunctions
    "the", "and", "for", "are", "but", "not", "you", "all", "can",
    "had", "her", "was", "one", "our", "out", "has", "his", "how",
    "its", "may", "did", "get", "got", "let", "say", "she", "too",
    "own", "with", "this", "that", "from", "they", "been", "have",
    "many", "some", "them", "than", "each", "which", "their",
    "will", "would", "could", "should", "about", "into", "over",
    "after", "before", "between", "under", "through", "during",
    # Greetings / chat words (expanded from _NOT_NAMES)
    "hi", "hey", "hello", "ok", "okay", "yes", "no", "sure", "thanks",
    "thank", "bye", "please", "help", "what", "how", "why", "when",
    "where", "who", "hii", "hiii", "nope", "yep", "yeah", "nah",
    "good", "fine", "great", "cool", "nice", "hmm", "umm", "lol",
    "haan", "ji", "nahi", "kya", "kaise", "kyun", "nhi", "haa",
    # Sentences / phrases that aren't names
    "not", "none", "pass", "skip", "later", "next", "done", "quit",
    "exit", "stop", "cancel", "whatever", "dunno", "idk",
    # Numbers as words
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "hundred", "thousand", "million",
    # Common Hindi/informal fillers
    "okh", "okk", "okayy", "ohk", "ohh", "ahh", "umm", "ugh", "ooh",
    "accha", "acha", "thik", "theek", "sahi", "haa", "haan", "nahi",
    "kya", "kaise", "kyun", "kab", "yaar", "bhai", "didi", "sir",
    "madam", "mam", "any", "some",
}

_CONVERSATIONAL_MARKERS = {
    "thank", "thanks", "thankyou", "please", "sorry", "okay", "okh",
    "ohk", "bye", "hello", "hey", "welcome", "sir", "madam", "mam",
    # Hindi filler words that appear after names (e.g. "Rohit hai" → "hai" is not part of the name)
    "hai", "hain", "hun", "hoon", "bol", "baat", "suno", "bhai",
    "ji", "sahab", "yaar", "dost",
}

_KNOWN_SHORT_NAMES = {
    "al", "bo", "ed", "jo", "li", "lu", "mo", "qi", "xu", "yi",
    "aj", "dj", "jd", "jp", "jr", "kc", "rj", "tj",
}

_GIBBERISH = {"abc", "xyz", "aaa", "bbb", "ccc", "test", "asdf", "qwerty", "foo", "bar"}

_SENTENCE_STARTERS = {
    "i", "we", "they", "he", "she", "it", "my", "our", "the",
    "this", "that", "what", "how", "why", "when", "where", "who",
    "can", "would", "could", "should", "do", "does", "did",
    "is", "am", "are", "was", "were", "have", "has", "had",
    "let", "please", "just", "not", "don", "doesn", "didn",
}


def _is_valid_name(text: str) -> bool:
    """Check if the given text looks like a real person's name.

    Rejects common English words (verbs, adjectives, adverbs, nouns),
    single characters, numbers, and other non-name patterns.
    """
    cleaned = text.strip().rstrip("!.,")
    if not cleaned:
        return False

    words = cleaned.split()
    # Must be 1-3 words
    if len(words) < 1 or len(words) > 3:
        return False

    # Each word must be alphabetic and 2+ chars
    for w in words:
        if not w.isalpha() or len(w) < 2:
            return False

    # Reject if ALL words are in the not-a-name set
    # (For multi-word: if ANY word is a valid name part, allow it — e.g., "John Good" is fine)
    lower_words = [w.lower() for w in words]
    if all(w in _NOT_A_NAME_WORDS for w in lower_words):
        return False

    # For single-word replies, must not be a common English word
    if len(words) == 1 and lower_words[0] in _NOT_A_NAME_WORDS:
        return False

    # Reject phrases containing conversational words (e.g. "Okh Thank You", "Ok Please")
    if len(words) >= 2 and any(w in _CONVERSATIONAL_MARKERS for w in lower_words):
        return False

    # Reject very short words (2 chars) that aren't known short names
    for w in lower_words:
        if len(w) == 2 and w not in _KNOWN_SHORT_NAMES:
            return False

    # Reject common test/gibberish patterns
    if any(w in _GIBBERISH for w in lower_words):
        return False

    # Reject if it looks like a sentence (has common verb/pronoun/determiner as first word)
    if len(words) >= 2:
        # Only reject if second word is ALSO a common word (allows "Will Smith", "Grace Lee")
        if lower_words[0] in _SENTENCE_STARTERS and lower_words[1] in _NOT_A_NAME_WORDS:
            return False

    return True


_NAME_ASKING_PHRASES = [
    "what should i call you",
    "what's your name",
    "what is your name",
    "who do i have the pleasure",
    "who am i chatting with",
    "who am i speaking with",
    "may i know your name",
    "can i get your name",
    "what do i call you",
    "who do i have the pleasure of chatting with",
]

# Pattern to validate a short-reply name (1-3 properly capitalized words)
_SHORT_NAME_RE = re.compile(r'^([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]+){0,2})$')

# Case-insensitive name fallback (for "my name is vijay" in any case)
_NAME_CI = re.compile(
    r"(?:i'?m|my\s+name\s+is|name\s+is|call\s+me|i\s+am"
    r"|mera\s+naam(?:\s+hai)?|naam\s+hai\s+mera)\s+"
    r"([a-z]{2,}(?:\s+[a-z]{2,}){0,2})",
    re.IGNORECASE,
)

# Explicit name intro pattern (used by extract_name_from_short_reply)
_INTRO_RE = re.compile(
    r"(?:my\s+name\s+is|i'?m|i\s+am|call\s+me|this\s+is"
    r"|mera\s+naam(?:\s+hai)?|naam\s+hai\s+mera)\s+"
    r"([a-z]{2,}(?:\s+[a-z]{2,}){0,2})",
    re.IGNORECASE,
)

# ── Intent classification ──
# Two-tier: phrases (substring match, checked first) + words (word-boundary match)
# Order matters: first match wins. More specific intents go first to avoid
# broad categories (like "services") swallowing them.

_INTENT_RULES = {
    "high_intent": {
        "phrases": [
            "ready to buy", "when can we start", "let's move forward",
            "lets move forward", "send a proposal", "send proposal",
            "next steps", "how do we proceed", "how to proceed",
            "let's get started", "lets get started", "sign us up",
            "we want to go ahead", "go ahead with", "finalize the deal",
            "close the deal", "ready to proceed", "want to proceed",
            "move ahead", "let's do this", "lets do this",
        ],
        "words": [
            "proposal", "contract", "agreement", "onboard", "onboarding",
        ],
    },
    "budget_signal": {
        "phrases": [
            "what's the roi", "whats the roi", "return on investment",
            "value for money", "budget approved", "within our budget",
            "within budget", "cost effective", "cost-effective",
            "worth the investment", "justify the cost",
            "what's the value", "total cost of ownership",
            "payback period", "break even",
        ],
        "words": [
            "roi", "profitability", "budget",
        ],
    },
    "decision_maker": {
        "phrases": [
            "my boss", "our ceo", "management wants", "board meeting",
            "present to stakeholders", "need approval", "get approval",
            "decision maker", "decision-maker", "my manager",
            "our director", "our vp", "present to management",
            "present to the board", "pitch to", "convince my",
            "share with my team", "share with management",
            "need to present", "have to present", "presenting to",
            "present to my", "present to our", "present to the",
            "present it to", "present this to",
        ],
        "words": [
            "stakeholder", "stakeholders", "boardroom",
        ],
    },
    "competitor_comparison": {
        "phrases": [
            "compared to", "better than", "why should we choose you",
            "your competitors", "how are you different from",
            "what makes you different", "vs ", "versus ",
            "why not go with", "why choose you over",
            "how do you compare", "what's your edge",
            "whats your edge", "advantage over",
            "how are you different",
        ],
        "words": [
            "competitor", "competitors", "alternative", "alternatives",
            "comparison", "differentiator",
        ],
    },
    "pricing": {
        "phrases": [
            "how much", "payment terms", "per square foot", "sq ft rate",
            "ballpark figure", "emi option", "cost per", "charge for",
            "rate card", "going rate", "per sqft",
            "get a quote", "get a estimate", "get an estimate",
            "need a quote", "need an estimate", "want a quote",
            "send a quote", "send an estimate", "provide a quote",
            "share a quote", "custom quote", "personalized quote",
        ],
        "words": [
            "price", "pricing", "cost", "rate", "fee", "charge",
            "quote", "estimate", "affordable", "expensive", "investment",
            "discount", "payment", "cheapest", "tariff", "billing", "invoice",
            "package", "packages",
        ],
    },
    "contact": {
        "phrases": [
            "get in touch", "speak with", "speak to", "phone number",
            "email address", "office phone", "office address", "office located",
            "who handles", "who should", "who manages", "who reviews",
            "who arranges", "how to contact", "how to reach",
            "new business", "media queries", "office tour",
            "whatsapp number", "whatsapp", "point of contact",
            "contact details", "contact for", "who do i",
            "pr contact", "investor relations", "site visit",
            "vendor registration", "business email",
            "join as a partner", "email for proposals",
            "call me back", "call me", "call us",
            "where is your office", "your office",
        ],
        "words": [
            "contact", "reach", "connect",
        ],
    },
    "demo": {
        "phrases": [
            "schedule a", "set up a", "book a", "arrange a",
            "want to see", "like to see", "need to see",
            "in action", "present your", "present case",
            "bring samples", "capabilities presentation",
            "experience it", "see a sample", "see the interactive",
            "want a walkthrough", "want a presentation",
            "want a capabilities", "can we visit",
            "do a demo", "on-site demo", "demo at",
            "can you demonstrate", "can we start",
        ],
        "words": [
            "demo", "demonstration", "demonstrate", "showcase",
            "walkthrough", "presentation", "meeting", "appointment",
        ],
    },
    "hiring": {
        "phrases": [
            "looking for designers", "looking for artists",
            "looking for developers", "looking for engineers",
            "any openings", "any opening", "open positions",
            "send my resume", "submit my resume", "send resume",
            "join your team", "join the team",
            "work culture", "growth at",
            "campus placement", "remote worker",
            "hr email", "apply online", "job fair",
            "hire from", "hire through",
            "do you need", "how to apply", "how to send",
            "how to join", "vacancy for",
            "offer internship",
        ],
        "words": [
            "hiring", "job", "career", "position", "vacancy",
            "recruitment", "intern", "internship", "fresher",
            "openings", "resume",
        ],
    },
    "services": {
        "phrases": [
            "what do you do", "what can you", "what kind of",
            "what all can", "help our", "help us", "help my",
            "do you do", "do you create", "do you make", "do you handle",
            "do you build", "do you design", "do you produce",
            "do you provide", "do you operate",
            "can you create", "can you build", "can you design",
            "can you produce", "can you make",
            "can you advise", "can you help",
            "virtual tour", "projection mapping", "holographic",
            "interactive kiosk",
            "marketing film", "tvc content", "social media content",
            "brochure visual", "print material",
            "brand activation", "event design",
            "augmented reality", "virtual reality", "mixed reality",
            "ar/vr", "your experience centre", "your experience center",
            "an experience centre", "an experience center",
            "need experience centre", "need a scale model",
            "project management", "tech choice",
            "what about maintenance", "what about support",
            "what about holographic", "what about cgi",
            "what about landscape", "what about social media",
            "what about ray", "what about project management",
            "how realistic", "what rendering",
            "what's your usp",
            "what's unique", "what's included",
            "end-to-end", "custom solution",
            "content creation", "spatial design",
            "how detailed", "what materials",
            "specialize in real estate", "something similar",
        ],
        "words": [
            "service", "offer", "provide", "solution", "capabilities",
            "specialize", "specialized", "specialization",
            "immersive", "visualization", "rendering",
            "render", "cgi", "animation", "flythrough", "aerial",
            "execution", "maintenance", "support", "technology",
            "kiosk", "consulting", "training", "photorealism",
            "unreal engine", "workflow",
        ],
    },
    "projects": {
        "phrases": [
            "case study", "case studies", "show me your", "show me the",
            "show me work", "show me ncr", "show me south",
            "show me residential", "show me retail", "show me lodha",
            "show me prestige", "show me your best", "show me your most",
            "show me your affordable", "show me your 3d",
            "show me your government", "show me your work",
            "done for", "created for", "built for",
            "what have you done", "what did you",
            "have you built", "have you created", "have you done",
            "have you delivered", "have you worked",
            "past work", "previous work", "recent work", "best work",
            "your work in", "your work for",
            "what work have", "what commercial",
            "what township", "what mixed-use", "what infrastructure",
            "what cgi films", "any work for",
            "any healthcare", "any hospitality",
            "any luxury", "any corporate office", "any brigade",
            "any award", "any international project",
            "any smart city", "any event installation",
            "any tata housing", "any projects in",
            "any government",
            "first big project",
            "portfolio of",
            "what about mahindra", "what about the sultan",
            "experience centres have you", "scale models have you",
            "hospitality experience centre",
            "worked with", "brands have you",
            "big brands", "clients have you",
        ],
        "words": [
            "project", "portfolio", "client", "example",
            "exhibition", "installation",
        ],
    },
}

# ── Scoring signals ──

_SCORING_RULES = {
    "pricing": 20,
    "services": 10,
    "demo": 15,
    "projects": 10,
    "contact": 15,
    "high_intent": 25,
    "budget_signal": 20,
    "decision_maker": 20,
    "competitor_comparison": 15,
}

# Pre-compile word-boundary patterns at module load (avoids re.compile per message)
_COMPILED_WORD_PATTERNS = {
    intent: [re.compile(r'\b' + re.escape(w) + r's?\b') for w in rules.get("words", [])]
    for intent, rules in _INTENT_RULES.items()
}


_HINDI_FILLER_TRAIL = re.compile(
    r'\s+(?:hai|hain|h[uo]+n|bol|bolo|bhai|ji|yaar|sahab)\s*$',
    re.IGNORECASE,
)


def _clean_name(name: str) -> str:
    """Strip trailing Hindi filler words from a captured name."""
    return _HINDI_FILLER_TRAIL.sub('', name).strip()


def extract_contact_info(message: str) -> dict | None:
    """Extract email, phone, and/or name from a user message. Returns dict or None."""
    result = {}

    email_match = _EMAIL_RE.search(message)
    if email_match and _is_valid_email(email_match.group()):
        result["email"] = email_match.group()

    phone_match = _PHONE_RE.search(message)
    if phone_match:
        phone = phone_match.group().strip()
        if _is_valid_phone(phone):
            result["phone"] = phone

    name_match = _NAME_PATTERNS.search(message)
    if name_match:
        # Multiple capture groups — pick the first non-None one
        name = next((g for g in name_match.groups() if g), None)
        if name:
            name = _clean_name(name)
            if _is_valid_name(name):
                result["name"] = name.strip().title()

    # Fallback: case-insensitive match for common intro phrases
    # Handles "my name is vijay", "i'm rahul", "call me priya" in any case
    if "name" not in result:
        ci_match = _NAME_CI.search(message)
        if ci_match:
            name = _clean_name(ci_match.group(1))
            if _is_valid_name(name):
                result["name"] = name.strip().title()

    return result if result else None


def extract_name_from_short_reply(user_message: str, previous_bot_message: str) -> str | None:
    """Detect name from a short reply when the bot just asked for it.

    This function is intentionally conservative — it only returns a name
    when it's highly confident. The primary name extraction now happens
    via LLM in rag_pipeline.py, and the name is saved from the bot's
    "Nice to meet you, X!" response.
    """
    if not previous_bot_message:
        return None

    bot_lower = previous_bot_message.lower()
    asked_for_name = any(phrase in bot_lower for phrase in _NAME_ASKING_PHRASES)
    if not asked_for_name:
        return None

    cleaned = user_message.strip().rstrip("!.,")

    # Only accept names explicitly introduced with a phrase like
    # "my name is X", "I'm X", "call me X", "mera naam X hai"
    intro_match = _INTRO_RE.search(cleaned)
    if intro_match:
        name = _clean_name(intro_match.group(1))
        if _is_valid_name(name):
            return name.strip().title()

    return None


def classify_intent(message: str) -> str:
    """Classify the user's intent from their message. Returns intent category."""
    msg_lower = message.lower()

    # First pass: multi-word phrases (substring match — more specific)
    for intent, rules in _INTENT_RULES.items():
        for phrase in rules.get("phrases", []):
            if phrase in msg_lower:
                return intent

    # Second pass: single/stem words with pre-compiled word-boundary patterns
    for intent, patterns in _COMPILED_WORD_PATTERNS.items():
        for pat in patterns:
            if pat.search(msg_lower):
                return intent

    return "general"


def calculate_score(session_data: dict) -> int:
    """Calculate lead score (0-100) based on session signals.

    session_data should have:
        - message_count: int
        - intents: list[str]  (classified intents from each message)
        - has_email: bool
        - has_phone: bool
        - has_name: bool
        - suggestion_clicks: int
        - positive_feedback: int
        - chat_opened: bool
    """
    score = 0

    # Chat opened
    if session_data.get("chat_opened"):
        score += 5

    # Intent-based scoring
    intents = session_data.get("intents", [])
    scored_intents = set()
    for intent in intents:
        if intent in _SCORING_RULES and intent not in scored_intents:
            score += _SCORING_RULES[intent]
            scored_intents.add(intent)

    # Combo bonus: multiple high-value intents together
    _HIGH_VALUE_INTENTS = {"high_intent", "budget_signal", "decision_maker", "pricing", "demo"}
    high_value_count = len(scored_intents & _HIGH_VALUE_INTENTS)
    if high_value_count >= 4:
        score += 25
    elif high_value_count >= 3:
        score += 20
    elif high_value_count >= 2:
        score += 10

    # Name provided
    if session_data.get("has_name"):
        score += 5

    # Contact info shared
    if session_data.get("has_email"):
        score += 25
    if session_data.get("has_phone"):
        score += 15

    # Engagement
    msg_count = session_data.get("message_count", 0)
    if msg_count > 5:
        score += 5

    # Suggestion clicks
    if session_data.get("suggestion_clicks", 0) > 0:
        score += 5

    # Positive feedback
    if session_data.get("positive_feedback", 0) > 0:
        score += 5

    return min(score, 100)


def build_session_data(session_id: str) -> dict:
    """Build session data dict from database for scoring. Uses 2 queries instead of 6.

    Uses stored intent column when available (avoids re-classifying all messages).
    """
    from backend import database as db

    conn = db._get_conn()

    # Query 1: Get user messages with stored intents + lead info
    messages = conn.execute(
        "SELECT content, intent FROM conversations WHERE session_id = ? AND role = 'user'",
        (session_id,)
    ).fetchall()
    # Use stored intent if available, otherwise classify on the fly
    intents = [
        m["intent"] if m["intent"] else classify_intent(m["content"])
        for m in messages
    ]

    lead = conn.execute(
        "SELECT email, phone, name FROM leads WHERE session_id = ?",
        (session_id,)
    ).fetchone()

    # Query 2: Single SELECT with scalar subqueries for analytics/feedback counts
    counts = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM analytics WHERE session_id = ? AND event_type = 'suggestion_clicked') as suggestion_clicks,
            (SELECT COUNT(*) FROM feedback WHERE session_id = ? AND feedback = 'up') as positive_feedback,
            (SELECT COUNT(*) FROM analytics WHERE session_id = ? AND event_type = 'chat_opened') as chat_opened
    """, (session_id, session_id, session_id)).fetchone()

    return {
        "message_count": len(messages),
        "intents": intents,
        "has_email": bool(lead and lead["email"]) if lead else False,
        "has_phone": bool(lead and lead["phone"]) if lead else False,
        "has_name": bool(lead and lead["name"]) if lead else False,
        "suggestion_clicks": counts["suggestion_clicks"],
        "positive_feedback": counts["positive_feedback"],
        "chat_opened": counts["chat_opened"] > 0,
    }


def should_capture_lead(message_count: int, current_score: int) -> bool:
    """Determine if we should add a soft CTA to capture lead info."""
    # After 2+ messages with some engagement but not yet a hot lead
    return message_count >= 2 and current_score >= 10 and current_score < 60


# ── Email engagement → lead score integration ──

def update_score_from_email_event(lead_id: int, event_type: str):
    """Update lead score based on email engagement events."""
    from backend import database as db

    conn = db._get_conn()
    lead = conn.execute("SELECT session_id, lead_score FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not lead:
        return

    bonus = 0
    if event_type == "open":
        bonus = 5
    elif event_type == "click":
        bonus = 10

    if bonus > 0:
        new_score = min((lead["lead_score"] or 0) + bonus, 100)
        db.update_lead_score(lead["session_id"], new_score)

        # Check sequence triggers
        try:
            from backend.email_service import sequences as email_sequences
            email_sequences.check_triggers(lead_id, "score_update", {"score": new_score})
        except Exception:
            pass
