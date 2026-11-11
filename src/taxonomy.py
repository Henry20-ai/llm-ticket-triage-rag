"""The business rules of the fictional company, defined once and reused by every script.

Brightcart is a fictional online store selling electronics and home goods.
The triage prompt (later step) uses exactly these categories and priority definitions,
so the generator, the classifier and the evaluation all speak the same language.
"""

COMPANY_CONTEXT = (
    "Brightcart is a fictional online store that sells electronics and home goods "
    "and delivers nationwide. Customers contact support through a web form."
)

TAXONOMY_VERSION = "v2"

CATEGORIES = {
    "Billing & Payments": "Charges, double charges, failed or declined payments, invoices and receipts, promo codes not applying or applied after checkout.",
    "Delivery & Shipping": "Late or missing parcels, tracking not updating, wrong delivery address, delivery to the wrong place.",
    "Returns & Refunds": "Return requests for items that are fine (change of mind, wrong size), return labels, refund delays, refund amount questions.",
    "Account & Access": "Cannot log in, password reset problems, locked account, changing email or phone, two-factor codes.",
    "Product Issue": "Damaged, defective or wrong items, missing parts, product not working as described. Includes requests to return or refund such an item.",
    "App & Website Issues": "Website or app bugs, checkout errors, crashes, pages not loading, forms that do not work. Includes any malfunction that blocks an action.",
    "General Inquiry": "General questions NOT tied to an action on a specific order: policies, opening hours, product information, general feedback.",
}

# Tie-break rules for category (v2). Used in the labelling guide AND in the triage prompt.
CATEGORY_RULES = [
    "A general question about policy, with no action needed on a specific order, is General Inquiry (for example: how long is the return window?). A request about a specific order goes to its topic category.",
    "Invoices, receipts and promo codes are always Billing & Payments.",
    "If an item is defective or damaged, choose Product Issue, even when the customer asks for a return or a refund.",
    "If a website or app malfunction is what blocks the customer (even from changing an address or logging in), choose App & Website Issues.",
    "If a ticket contains several issues, choose the one with the most money at risk.",
]

PRIORITIES = ["Low", "Medium", "High", "Urgent"]

PRIORITY_GUIDE = {
    "Urgent": "Money charged or lost without a clear explanation (for example a failed payment with the money held, or a double charge), an account compromise, a safety hazard, or a site outage.",
    "High": "The customer is blocked from paying, logging in or receiving a time-sensitive order.",
    "Medium": "Something is broken or overdue, with no deadline.",
    "Low": "A question, information request, feedback or a cosmetic issue. Nothing is broken.",
}

# Invented example tickets (NOT taken from the database) shown to the model in the triage prompt.
EXAMPLES = [
    ("How long do I have to return something after it arrives?", "General Inquiry", "Low"),
    ("Can you email me a copy of the invoice for my order BC-111111?", "Billing & Payments", "Low"),
    ("The payment page froze and now my bank shows the money as held but I have no order confirmation.", "Billing & Payments", "Urgent"),
    ("My kettle arrived with a cracked lid and I would like my money back.", "Product Issue", "Medium"),
    ("The speaker has a tiny scratch on the back. It works fine, just letting you know.", "Product Issue", "Low"),
    ("My parcel was due last Tuesday and tracking has not moved for 4 days. No rush, just checking where it is.", "Delivery & Shipping", "Medium"),
    ("The address field on the order page will not let me type and my order ships tomorrow. I need it sent to my office.", "App & Website Issues", "High"),
    ("There are three orders on my account that I never placed, and I got a password-change email I did not request.", "Account & Access", "Urgent"),
    ("My blender smelled of burning when I switched it on and sparks came out of the base.", "Product Issue", "Urgent"),
]

# How many tickets to generate per category, and how priorities are spread inside the
# category as weights in the order [Low, Medium, High, Urgent]. Total = 420 tickets.
TICKET_PLAN = {
    "Billing & Payments": (80, [10, 30, 35, 25]),
    "Delivery & Shipping": (90, [15, 40, 30, 15]),
    "Returns & Refunds": (60, [20, 45, 25, 10]),
    "Account & Access": (50, [10, 30, 40, 20]),
    "Product Issue": (50, [15, 40, 30, 15]),
    "App & Website Issues": (50, [15, 35, 35, 15]),
    "General Inquiry": (40, [60, 30, 8, 2]),
}

# Writing styles, so the tickets do not all sound the same.
STYLES = [
    "polite and detailed",
    "angry and short",
    "confused and vague",
    "professional, includes the order number",
    "casual, with a couple of typos",
    "calm but worried",
    "very brief, one or two sentences",
]

PRODUCTS = [
    "wireless earbuds", "air fryer", "55-inch smart TV", "laptop stand", "robot vacuum",
    "bluetooth speaker", "standing desk", "electric kettle", "phone charger", "desk lamp",
    "coffee maker", "gaming mouse", "security camera", "blender", "tablet",
]
