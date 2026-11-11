# Website Outage and Degraded Service

## Purpose
This SOP outlines the protocol for identifying, reporting, and managing large-scale website or app disruptions at Brightcart. The goal is to ensure consistent communication and rapid resolution when technical issues prevent customers from using our platform.

## When this applies
This procedure applies when customers report technical errors, such as site crashes, checkout failures, or broken page elements. If more than 3 customers report the same website or app problem within a 30-minute window, the situation must be treated as a possible outage.

## Steps for the agent
1. **Identify the Pattern:** Check the ticket queue for recurring reports of the same issue. If the threshold of 3 reports in 30 minutes is met, immediately label the ticket as "Urgent."
2. **Verify the Issue:** Attempt to replicate the reported behavior on the live site. Do not clear your browser cache or use incognito mode initially, as this may hide the issue from the customer's perspective.
3. **Notify Engineering:** Contact the Engineering on-call representative via the internal communication channel immediately. Provide a clear description of the error, the number of affected users, and any relevant screenshots or error codes.
4. **Update the Ticket:** Once notified, add an internal note to all related tickets stating: "Engineering notified at [Time]. Investigation in progress."
5. **Monitor and Update:** Check for updates from Engineering every 30 minutes. If the issue is resolved, update all affected tickets with the resolution and close them according to standard policy.

## What to tell the customer
"I sincerely apologize for the trouble you are experiencing with our website. Our technical team is currently investigating this issue as a priority to get everything back up and running for you. I have logged your report and will notify you as soon as we have an update on the fix."

## Escalation and priority
*   **Urgent:** Any confirmed outage or technical issue preventing checkout or account access for multiple users. Escalation to Engineering is mandatory within the first 15 minutes of identifying the pattern.
*   **High:** An issue affecting a single user’s ability to complete an important action (e.g., payment or login) that does not qualify as a site-wide outage.
*   **Medium:** Minor interface glitches or bugs that have a clear, inconvenient workaround.
*   **Low:** General feedback or cosmetic issues that do not impact functionality.

## Common mistakes
*   **Failure to Aggregate:** Treating reports as isolated incidents rather than checking for a broader pattern, which delays the identification of an outage.
*   **Over-promising:** Providing specific timelines for a fix before Engineering has confirmed the root cause. Always stick to the status provided by the technical team.
*   **Ignoring Support Hours:** Failing to notify the on-call agent for Urgent tickets outside of 08:00–20:00, Monday to Saturday. Always ensure the on-call agent is alerted regardless of the time if the issue meets the "Urgent" criteria.