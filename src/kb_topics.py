"""The fictional company's facts and the list of SOP documents to write.

POLICY_FACTS is given to Gemini for EVERY document, so all 25 SOPs agree with each other
(same return window, same refund times, same escalation rules).
"""

POLICY_FACTS = """
- Support hours: 08:00-20:00, Monday to Saturday. An on-call agent watches Urgent tickets outside those hours.
- Response targets: Urgent 1 hour, High 4 hours, Medium 1 business day, Low 2 business days.
- Delivery: standard 3-5 business days, express 1-2 business days. A parcel is "late" once it is 2 business days past its estimated date and "lost" 7 business days past it.
- Returns: allowed within 30 days of delivery, item unused and in original packaging. Defective, damaged or wrong items are returned free with a prepaid label. Change-of-mind returns cost a flat $5 label fee, deducted from the refund. Opened electronics carry a 10% restocking fee for change-of-mind returns.
- Refunds: to a card within 5-7 business days after the return is received and inspected (inspection takes up to 2 business days). Store credit is instant. Bank transfer takes 3-5 business days.
- Double charges: verify within 1 business day. A confirmed duplicate is refunded in full within 5 business days. Agents may refund up to $200 alone; above $200 a manager must approve.
- Failed or declined payments: a held authorisation drops automatically in 3-5 business days. The order is not placed if payment failed.
- Promo codes: one code per order; expired codes cannot be reapplied. If a code failed because of a system fault, a team lead can approve honouring it.
- Warranty: electronics 12 months from delivery, home goods 6 months.
- Damaged on arrival: customer must report within 7 days with photos. They choose a replacement or a full refund.
- Account security: an account locks for 30 minutes after 5 failed logins. Password-reset links expire after 30 minutes. Two-factor codes are valid for 5 minutes and can be reset after identity verification (email plus last order number). Changing email or phone requires a code sent to the OLD contact method.
- Suspected account compromise is always Urgent: lock the account, force a password reset, review the last 30 days of orders, and escalate to the Security team within 15 minutes.
- Outages: if more than 3 customers report the same website or app problem within 30 minutes, treat it as a possible outage, mark it Urgent and notify Engineering on-call.
- Contact channels: support web form, email support@brightcart.example, live chat during support hours.
""".strip()

# (title, category it mainly supports, what the document should cover)
SOP_TOPICS = [
    ("Handling a Double Charge", "Billing & Payments", "A customer sees the same order charged twice. Verification, refund limits and approvals."),
    ("Failed and Declined Payments", "Billing & Payments", "Payment fails at checkout or a held authorisation appears. What it means and what to tell the customer."),
    ("Promo Codes and Discounts Not Applying", "Billing & Payments", "Codes that fail, expire or cannot be combined."),
    ("Invoices and Receipts", "Billing & Payments", "Customers asking for invoices, receipts or billing details to be corrected."),
    ("Late Deliveries and Delays", "Delivery & Shipping", "Parcel is past its estimated date. When it counts as late, what to check, what to offer."),
    ("Lost or Missing Parcels", "Delivery & Shipping", "Tracking says delivered but the customer has nothing, or the parcel is lost. Investigation and replacement or refund."),
    ("Wrong or Incomplete Delivery Address", "Delivery & Shipping", "Customer entered the wrong address or needs to change it. What can be changed before and after dispatch."),
    ("Tracking Not Updating", "Delivery & Shipping", "Tracking page is stuck or shows no movement."),
    ("Return Eligibility and the 30-Day Window", "Returns & Refunds", "Who can return what, conditions, exceptions."),
    ("Issuing Return Labels", "Returns & Refunds", "Creating and resending prepaid labels, costs for change-of-mind returns."),
    ("Refund Timelines by Payment Method", "Returns & Refunds", "How long refunds take by card, store credit and bank transfer, and how to answer 'where is my refund'."),
    ("Partial Refunds and Restocking Fees", "Returns & Refunds", "When a refund is reduced, how fees are calculated."),
    ("Password Resets and Locked Accounts", "Account & Access", "Customer cannot log in, reset link problems, lockouts."),
    ("Two-Factor Authentication Problems", "Account & Access", "Codes not arriving, expired codes, lost phone, resetting 2FA after verification."),
    ("Changing Email or Phone Number", "Account & Access", "Verification steps required before contact details can change."),
    ("Suspected Account Compromise", "Account & Access", "Customer reports unknown orders, logins or changes. Security incident handling."),
    ("Items Damaged on Arrival", "Product Issue", "Report window, photos, replacement or refund choice."),
    ("Defective Products and Warranty Claims", "Product Issue", "Product stopped working or does not work as described. Warranty periods and steps."),
    ("Wrong Item or Missing Parts", "Product Issue", "Customer received a different item or an incomplete product."),
    ("Checkout Errors and Cart Problems", "App & Website Issues", "Checkout fails, cart empties, buttons do nothing. Troubleshooting and escalation."),
    ("App Crashes and Bug Reports", "App & Website Issues", "App closes or freezes. Information to collect and how to log a bug."),
    ("Website Outage and Degraded Service", "App & Website Issues", "Many customers affected. How to recognise an outage and who to notify."),
    ("Priority and Escalation Guidelines", "General Inquiry", "How agents decide Low, Medium, High or Urgent for any ticket, with examples for each, and response targets."),
    ("Customer Communication Standards", "General Inquiry", "Tone, wording, apologies, what never to promise, how to close a ticket."),
    ("Store Policies, Hours and Contact Channels", "General Inquiry", "Frequently asked questions about hours, channels, shipping options and general policies."),
]
