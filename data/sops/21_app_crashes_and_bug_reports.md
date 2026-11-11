# App Crashes and Bug Reports

## Purpose
This SOP defines the standardized process for handling customer reports regarding Brightcart app crashes, freezes, or unexpected behavior. The goal is to gather sufficient technical data to allow our Engineering team to reproduce and resolve the issue efficiently.

## When this applies
Use this procedure when a customer reports that the Brightcart mobile app or website closes unexpectedly, becomes unresponsive (freezes), or displays a persistent technical error message that prevents navigation or shopping.

## Steps for the agent
1. **Acknowledge and Validate:** Confirm receipt of the report and apologize for the disruption to their shopping experience.
2. **Gather Technical Data:** Request the following specific information from the customer:
   - Device model (e.g., iPhone 13, Samsung Galaxy S22).
   - Operating system version (e.g., iOS 16.2, Android 13).
   - Brightcart App version (found in the app settings).
   - Specific steps taken immediately before the crash (e.g., "I clicked the checkout button after adding a toaster to my cart").
   - Any error codes or messages displayed.
3. **Check for Outages:** If you receive more than three reports of the same app or website issue within a 30-minute window, treat this as a possible outage. Immediately mark the ticket as **Urgent**, notify the Engineering on-call team, and alert your supervisor.
4. **Log the Bug:** Create a ticket in the internal bug tracker. Include the gathered technical data, a link to the customer’s ticket, and a clear summary of the reproduction steps.
5. **Follow Up:** Provide the customer with a reference number and inform them that our technical team is investigating the matter.

## What to tell the customer
"I am very sorry to hear that you are experiencing issues with the app, and I understand how frustrating it is to have your shopping interrupted. To help our technical team investigate this, could you please provide your device model, operating system version, and the specific steps you took right before the app closed? Once I have those details, I will log this with our developers immediately to get it resolved."

## Escalation and priority
*   **Urgent:** If the issue involves a suspected account compromise or if more than three customers report the same issue within 30 minutes (possible outage).
*   **High:** If the customer is completely blocked from completing a purchase or accessing their account.
*   **Medium:** If the app is crashing during non-essential browsing or if there is a known workaround.
*   **Low:** Minor visual glitches or UI annoyances that do not prevent the customer from using the app.

## Common mistakes
*   **Failing to ask for device details:** Without the OS version and device model, Engineering cannot replicate the environment.
*   **Ignoring outage thresholds:** Failing to flag a pattern of reports delays the identification of site-wide outages.
*   **Guessing the fix:** Never instruct a customer to reinstall the app or clear cache without first logging the bug; we need the data captured before the state is reset.