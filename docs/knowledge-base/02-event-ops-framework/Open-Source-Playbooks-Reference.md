# Open-Source Event Playbooks: Extracted Reference

Verbatim extracts from public GitHub repositories that publish event operations
documentation under open licenses. All content below is quoted from the source
files, not paraphrased. Verified against the GitHub API on 2026-08-11.

## Sourcing Corrections

Three of the four originally-specified sources do not exist at the stated
locations. The substitutions below are the actual repositories holding the
requested material.

| Specified | Status | Actual source used |
|---|---|---|
| `python-organizers/awesome-organizing` | **404 — does not exist** | `python-organizers/resources` + `python-organizers/conferences` |
| `cncf/foundation` (KubeCon venue specs, AV riders) | **Exists, but holds no venue/AV specs.** It is a governance/legal repo (charter, licence exceptions, trademark agreements). No KubeCon attendee-count ranges or AV rider templates are published anywhere in the CNCF org. | `cncf/communitygroups` for event ops; `cncf/foundation` for travel funding, D&O insurance, online-program AV |
| "Mozilla Event Checklist" | **No such open repo.** `mozilla/london-events-presentation` is a Jade/CSS slide deck marked `INACTIVE - http://mzl.la/ghe-archive`; `mozilla/community-ops` is `INACTIVE`, last pushed 2015-04-21. Neither contains ADA, captioning, or insurance guidance. | `mxsasha/lessobviouschecklist` (382 stars, live at lessobvious.cc) for accessibility/risk/attendee experience; `mozilla/inclusion` for CoC enforcement laddering |
| `devopsdays/devopsdays-web` | **Exists and is the richest source of the four.** | Used as specified |

No open-source repository publishes AV rider templates, decibel targets, or
console/PA specifications. That gap is real and applies to all four sources.

---

## 1. CNCF — `cncf/communitygroups` and `cncf/foundation`

### 1.1 Repository metadata

| Field | `cncf/communitygroups` | `cncf/foundation` |
|---|---|---|
| URL | https://github.com/cncf/communitygroups | https://github.com/cncf/foundation |
| Last push | 2026-06-10 | 2026-08-07 |
| Key file last commit | `best_practices.md` — 2026-05-29, "Update event registration link for CNCGs" | `travel_funding.md`, `do-insurance.md` |
| Licence | LICENSE present | Governance docs |

### 1.2 Key files to reference

- `best_practices.md` — https://github.com/cncf/communitygroups/blob/main/best_practices.md (261 lines; the host + organizer checklists)
- `organizers.md` — https://github.com/cncf/communitygroups/blob/main/organizers.md (team sizing, role split, vendor-neutrality caps)
- `meetups-vs-communityday.md` — https://github.com/cncf/communitygroups/blob/main/meetups-vs-communityday.md (event-tier definitions and attendee caps)
- `assets.md` — https://github.com/cncf/communitygroups/blob/main/assets.md (sponsor prospectus template, promo graphic templates)
- `travel_funding.md` — https://github.com/cncf/foundation/blob/main/travel_funding.md (scholarship timeline and reimbursement terms)
- `policies-guidance/online-programs-guidelines.md` — https://github.com/cncf/foundation/blob/main/policies-guidance/online-programs-guidelines.md (soundcheck windows, submission deadlines)
- `do-insurance.md` — https://github.com/cncf/foundation/blob/main/do-insurance.md

### 1.3 Attendee count ranges and event tiers

These are the only published CNCF numbers. They govern KCDs and Community Days,
not KubeCon itself.

From `meetups-vs-communityday.md`:

> Hosting meetups can be as simple as 1-2 hours of content + networking no matter what style you decide (speaker to audience, study groups, lightning talks, etc.).

> Hosting a Cloud Native Community Day is a great way to practice for a KCD. A Cloud Native Community Day can be like a large meetup where:
> * You have a one half (1/2) of a day of content - so 4 hours of multiple speakers.
> * You acquire sponsorships.
> * You provide breaks with beverages and/or food.
> * Your event must be free to attend like a meetup if these are hosted within your chapter.
> * These can be hosted as often as you would like with a reccomendation being no more than once per quarter.
> * There is no limit to the number of attendees.

On KCDs specifically:

> * These are 1 to 2 day events like a summit, and often times can host multiple tracks and keynotes.
> * KCDs can charge a fee for their tickets.
> * **KCD have a limit of 500 attendees.**
> * KCDs in the same city (and sometimes small country) can only be hosted once per year.

### 1.4 Overbooking and show-rate maths

From `best_practices.md`, the "Booking" section — the load-in headcount driver:

> If the room capacity limits you, you should do an **overbooking**.
>
> Most of the time, there are 30% of people who RSVP, but never come. Recently KCDs (1 to 2 day summit-like events have a 92% show rate).
>
> You should think about sending a **reminder** message to the meetup group to ask the people to free their place if they can't come.

### 1.5 Venue requirements

From `best_practices.md`, "Sponsorships" and "Preparation":

> It is better to find a place in a central location. Downtown would be ideal because it's easier to access for most of the attendees.

> If you're planning a hands-on demo, you should ensure that the WiFi can handle the number of attendees.
>
> Furthermore, you should check you're not limited by some quotas (Cloud provider).

> - **Guide attendees to the event location**: make sure the path from the street to the event location is labeled and clear
> - **Prepare the speaker room**: make sure you do a technical check, prepare chairs and all the equipment you might use
> - **Guide attendees at the venue**: label the way to restrooms, the elevator, terrace and only other places that are visited during the event. If the location has "restricted" areas, label those too.
> - **Food**: prepare a place to put the food (if you order for 100 people, this takes a lot of space), label ingredients for allergies and personal preference (vegan, halal food, …)

Scheduling constraint:

> The choice of date and time matters. Most meetups choose Tuesdays, Wednesdays, or Thursdays after work. But use your discretion, since every culture varies.

### 1.6 AV: what CNCF actually publishes

No AV rider template exists. The closest published technical requirements are
the equipment line items in the host checklist and the online-program soundcheck
window.

From `best_practices.md`, "Set up the event space":

> - [ ] Arrange seating, tables, and any necessary presentation equipment (e.g., projector, screen, microphones).
> - [ ] Test all equipment to ensure proper functionality.
> - [ ] Provide clear signage directing attendees to the event space, including a map showing washrooms.

From "Coordinate with speakers and organizers" — the adapter/clicker kit:

> - [ ] Ensure speakers have everything they need for their presentations (e.g., clicker/slide advancer, possibly USB and USB-C adapters for different machines).
> - [ ] Offer assistance in setting up and troubleshooting any presentation equipment.

The only published soundcheck duration, from `online-programs-guidelines.md`:

> * Live webinars
> 	* Only offered to Gold and Platinum members
> 	* **Day of webinar - 15 minute soundcheck**
> 	* Premiere date - Tuesdays or Wednesdays at 10am PT

A/V is named as a formal role assignment in `organizers.md`:

> We do however, suggest your team figure out who has more experience organizing different facets of community groups like:
> * Sponsorships
> * Speakers
> * F&B (Food and Beverage)
> * **A/V (Audio & Video)**
> * Swag
> * On-site emcee
> * Attendee marketing and communications
>
> NOTE: If your team is small, it is common to have 1-2 assignments per person.

### 1.7 Speaker management: slide submission workflow

From `best_practices.md`, "Manage communications ahead of the event" — this is the
full published pre-event speaker workflow:

> - [ ] Send speaker logistics ahead of time, including presentation time and setup requirements.
> - [ ] Request the speaker's headshot and preferred bio.
> - [ ] Ask to review their slides in advance to ensure there are no vendor pitches.
> - [ ] **Specify screen dimensions (considering 4:3 or 16:9 slide aspect ratio).**
> - [ ] Allocate Q&A time and any networking opportunities.
> - [ ] Build a survey for attendee feedback during the event and generate a QR code.
> - [ ] Create housekeeping slides to loop at the beginning and end of the event, including the QR code for the survey.

Show-caller duties during the event:

> - [ ] Serve as the emcee to address light housekeeping items and introduce speakers.
> - [ ] Monitor the event's schedule and gently remind the speaker(s) of time limits.
> - [ ] Assist with transitions between speakers or activities to maintain the event flow. Use this opportunity for housekeeping announcements.

On overruns, from "Hosting the event":

> - **Speaker times**: It often happens that a talk takes a little longer than anticipated or the audience is asking many questions. In smaller meetups you can be flexible about it, in bigger events you should interrupt and stick to the schedule.

CFP intake form and vendor-neutrality screen:

> You should provide a **form** to allow people to submit their talk proposal similar to this:
> https://docs.google.com/forms/d/1V2Y03YMOrIor0M796_WMbYx-fdsn80ngaT-PIum8gUU/edit
>
> > **_Note_**: Make a copy! Please do not edit that form.
>
> Pro Tip: Sessionize has a community license that you can apply for, if you host free community events. [Read more](https://sessionize.com/playbook/community-license)

> Vendor neutrality in the context of a conference session refers to the principle of maintaining an impartial and unbiased environment during the session, particularly when discussing products, services, or solutions offered by different vendors.

Sponsor stage-time cap:

> * Offer your sponsor no more than 15 minutes of talking time on the stage. But be sure they are NOT the main content.

### 1.8 Backup procedures

CNCF's published redundancy guidance is organizational, not technical:

> In order to remain a strong and active community, we believe CNCGs are successful with 2 or more organizers with responsibilities divided among each other. Ideally there is no more than 5 organizers for virtual chapters, and no more than 7 for in-person.

> You are already donating your time to further the knowledge and awareness of Cloud Native technologies, likely in addition to a full-time job. In addition, people may fall ill, get injured, or have new deadlines. With that, **it will benefit you to have backup to avoid cancellations of your meetups**.

> Each team should have no more than 50% of organizers from the same company. This is to assure fair voting practices, what's more --> vendor nuetrality.

### 1.9 Travel funding timeline

From `cncf/foundation/travel_funding.md` — the dated backbone of the scholarship process:

> 1. Event team will determine the close date and notification deadline.
>     - a. Deadline is based on schedule announcement, visa process time, speaker notifications, length of the review period.
>     - b. **Notifications made 6 - 8 weeks prior to event.**
>
> 2. Launch Application with link, information and dates on event website **4 months prior to the application deadline (6 months prior to event)**.

> 5. Event team provides committee with timeline for review process.
>     - a. The requirement is not to review on a rolling basis but rather wait for all applications to be submitted and then reviewed comprehensively.
>     - c. **Recommended review period for committee is 7-10 days** depending on the number of applicants and review committee availability.
>     - d. Once selections are made, 1 week is needed to process notifications internally.

> 7. Review committee reviews and scores applications and requests.
>     - a. Review committee to consider: **Impact, Outreach, and Equity.**

Reimbursement terms:

> - a. Expense reports and receipts must be submitted **within 30 days of completion of travel**. Reimbursement will be made within 30 business days after the final expense report has been submitted and approved.
> - b. It is the responsibility of the recipient to arrange, reserve, and pay for accommodations and/or flight directly. They will then be reimbursed for approved travel expenses not to exceed a maximum stipend amount. The stipend may only be used for **coach airfare, hotel/accommodations (up to five nights), and ground transportation (to and from the airport)**.
> - c. Attendance is required in order to be reimbursed.

### 1.10 Insurance

From `cncf/foundation/do-insurance.md`, in full — note this is D&O cover for
volunteers, **not** event liability or venue-required general liability:

> The Linux Foundation maintains a comprehensive umbrella of insurance policies to protect its communities' interests. This insurance covers the projects themselves, any employees of the organization and **extends to volunteers who are working with LF projects**. For those contributors who work on LF projects on behalf of member companies, those companies' own insurance policies also provide coverage and would most likely be the primary source of protection for those contributors.

---

## 2. python-organizers — `resources` and `conferences`

### 2.1 Repository metadata

| Field | `python-organizers/resources` | `python-organizers/conferences` |
|---|---|---|
| URL | https://github.com/python-organizers/resources | https://github.com/python-organizers/conferences |
| Description | "Share docs, tools, lists and whatnot for organizing a Python conference" | "List of Python Conferences around the World" |
| Created | 2018-12-04 | — |
| **Last push** | **2020-10-01** (dormant ~6 years) | **2026-08-08** (active) |
| Stars | 59 | — |
| Licence | NOASSERTION | — |
| Contents | `README.rst` (222 lines) + one issue template | `2017.csv` … `2028.csv` |

**Reality check on this source.** The `resources` repo contains no checklists and
no budget templates. Its README is a 222-line scaffold of unanswered prompts —
many sections end in a literal `???` placeholder. The two sections the task asked
for read, in full:

> Sponsorship
> -----------
>
> ???

> Money
> -----
>
> - See The PSF's `Grants Program <https://www.python.org/psf/grants/>`_
> - How will you receive income? Do you need to create a non-profit org?
> - Will you have grants / financial aid for speakers / attendees?
> - Is there guideline of how much should be allocated for grants?
> - ???

There are no line-item categories and no vendor cost ranges anywhere in the repo.
For those, use the DevOpsDays budget breakdown in section 3.5 below, which is the
only source of the four that publishes actual currency figures.

### 2.2 What the repo does usefully provide: venue and date decision prompts

These are the substantive lists, quoted verbatim from `README.rst`:

> Choosing a Venue
> ----------------
>
> Things to consider:
>
> - accessibility (wheelchair, all inclusive bathrooms, nursing facilities, public transit, parking, etc)
> - equipment: projector, etc
> - does it provide catering? can you bring your own food/hire your own caterer? Do you even need caterer?
> - Sprint venue
> - Single track or multi track?
> - Tutorial/workshop venue
> - Space for sponsor booths
> - insurance

> Choosing a date
> ---------------
>
> Things to consider:
>
> - Will it conflict with other conferences? Does it matter?
> - Weekday vs weekend?
> - Will it conflict with a religious holiday? School holidays? Mother/Father's Day etc?

> Volunteers
> ----------
>
> - Are volunteers needed? (Registration, Info, Moderation, Tech Support, Food/Drinks, Setting up/Tearing down venue, ...)
> - How many?
> - Motivation to volunteer (Reduced/free entry, free shirt/food/drinks)

CFP scoping prompts:

> - When should CFP be started, ended, how long?
> - Will you have keynotes / invited speakers? How to choose a keynote?
> - How far ahead do you usually invite keynote speakers?
> - Will you have sponsored talks?
> - What types of events do you want to offer? (Workshops, Panels, Lectures, ...)
> - Length of slots (by type).
> - What information do you need? (Description for program, additional infos, requirements)
> - License agreement if you want to publish paper/abstract/video. (Recommend `CC-BY-4.0 <https://creativecommons.org/licenses/by/4.0/>`__)

### 2.3 Video licensing warning

The one piece of hard-won operational knowledge unique to this repo — a quoted
note from Ewa Jodlowska (then PSF Executive Director):

> We want to remind you all to review your speaker agreements and YouTube licenses to ensure they reflect the intentions of your event.
>
> The Creative Commons license (https://support.google.com/youtube/answer/2797468?hl=en) allows others to edit the videos you post. If you choose to go the route of Creative Commons, you should check that your speaker agreement allows this type of license arrangement.
>
> The YouTube Standard license allows sharing your content via play lists, unedited.
>
> We are not suggesting one way or another, we want to present the facts and let you all decide what works best for your event. **PyCon US recently experienced a situation that ended with us changing our YouTube license from Creative Commons to the Standard YouTube license.** We want all organizers to be informed of the options and consequences of each.

### 2.4 Tooling lists (verbatim, alphabetical as published)

CFP tools:

> - `Frab <https://github.com/frab/frab>`_
> - `Google Forms <https://www.google.ca/forms/about/>`_
> - `Papercall <https://www.papercall.io/>`_
> - `pretalx <https://pretalx.com/p/about/>`_
> - `Symposion <https://github.com/pinax/symposion>`_
> - `Yak Bak <https://gitlab.com/bigapplepy/yak-bak>`_ (developed/used by PyGotham)

Ticketing: Eventbrite, `pretix`, `Tito`. Volunteer scheduling: `Engelsystem`.
CoC tooling: `cache-rules/coc-hotline`, `Mariatta/enhanced-coc-hotline`.
Sponsorship: `froscon/SaBoT`.

### 2.5 The onward pointer that matters

The repo's own "Related resources" section is what led to source 4 in this
document:

> - `The Less Obvious Conference Checklist <https://github.com/mxsasha/lessobviouschecklist>`_ by Sasha Romijn
> - `How we designed an inclusivity-first conference on a shoestring budget and short timeline <https://www.youtube.com/watch?v=C7ZhMnfUKIA>`_ PyCon US talk by Christopher Neugebauer, Josh Simmons, and Sam Kitajima-Kimbrel

### 2.6 `conferences` repo: usable date-conflict data

The active sibling repo publishes one CSV per year with this schema, directly
usable for calendar-conflict checks:

```
Subject,Start Date,End Date,Location,Country,Venue,Tutorial Deadline,Talk Deadline,Website URL,Proposal URL,Sponsorship URL
PyConf Hyderabad 2026,2026-03-14,2026-03-15,"Hyderabad, Telangana, India",IND,Engineering Staff College of India,,2026-01-15,...
PyCascades,2026-03-21,2026-03-22,"Vancouver, British Columbia, Canada",CAN,SFU Harbour Centre,,2025-10-27,...
```

Files `2017.csv` through `2028.csv`. CI validates format via
`.github/workflows/validate.yaml`.

---

## 3. DevOpsDays — `devopsdays/devopsdays-web`

### 3.1 Repository metadata

| Field | Value |
|---|---|
| URL | https://github.com/devopsdays/devopsdays-web |
| Description | "This is the website for devopsdays" |
| Homepage | https://www.devopsdays.org |
| Created | 2015-11-09 |
| **Last push** | **2026-08-07** |
| Stars | 193 |
| Default branch | `main` |
| Repo size | 51,410 tracked paths |

### 3.2 Key files to reference

- `content/page/organizing.md` — https://github.com/devopsdays/devopsdays-web/blob/main/content/page/organizing.md — **the primary artefact, 796 lines.** Last commit 2026-06-02, "[core] remove stale wording from rule (#15937)". Front matter `title = "Devopsdays - Organizing Guide"`, `date = "2023-11-06T23:40:47-06:00"`.
- `content/page/sponsor.md` — sponsorship guidelines
- `content/page/conduct.md` — global CoC
- `content/page/open-space-format.md` and `content/page/ignite-talks-format.md` — session format specs
- `utilities/docs/cancel-event.md` — https://github.com/devopsdays/devopsdays-web/blob/main/utilities/docs/cancel-event.md — cancellation runbook
- `utilities/examples/content/events/yyyy-city/conduct.md` — CoC template referenced as required before PR merge
- `utilities/add_new_event.sh`, `add_organizers.sh`, `add_program.sh`, `add_speakers.sh`, `add_sponsors.sh` — scaffolding scripts
- `.github/workflows/no-sponsors-changes.yml` — CI guard on sponsor data

### 3.3 Non-negotiable structural rules

> - Inclusiveness and respect for differences are core devops values, and we invite you to help us make each devopsdays event a place that is welcoming and respectful to all participants. Your event will need to have a code of conduct.
> - These are community events, so your event must have an open call for proposals and accept registrations from the general public.
> - Sponsors are much appreciated for their financial assistance, and they are welcome to participate in devopsdays events. **They are never given attendee contact info** by a devopsdays event's organizers, **nor are they allowed to purchase speaking slots** for talks or ignites at a devopsdays.

Team composition floor:

> You're going to need **at least three people from three different organizations** on your local organizing team, so you have a broader base of support and involvement from the community. We aren't going to green-light events put on by just one company.

### 3.4 Team breakdown: roles and responsibilities

The task asked for a Logistics / Program / Sponsors / Marketing split. DevOpsDays
publishes a finer-grained nine-way split instead, from "Distributing the work",
verbatim:

> Effective delegation is key to ensuring the smooth organization of your event. It's advisable to divide responsibilities among your organizing team to allow focused attention on different tasks. While the following distribution is a suggestion and not prescriptive, it can provide a starting point:
>
> - **Talk Proposals**: Assign a person or a pair to manage and review talk submissions.
> - **Ignite Proposals**: Delegate someone to handle ignite talk submissions.
> - **Website Updates**: Designate a person or a pair to maintain and update the event's website.
> - **Speakers**: Designate a person or pair to handle all speaker communications, so speakers have a clear point of contact ensuring that all their details are in place.
> - **Sponsorships**: Assign responsibilities for liaising with sponsors, managing agreements, and ensuring deliverables.
> - **Registration & Invoicing**: Designate someone to oversee attendee registrations, handle invoicing, and respond to related queries.
> - **Venue & Local Logistics**: This includes managing the venue, catering, local arrangements, and hotel bookings.
> - **Merchandise**: Assign a person or a pair to handle merchandise, such as t-shirts.
> - **Evening Event Logistics**: Delegate responsibilities for organizing any evening activities or gatherings.

Mapped to the four-team model requested:

| Team | DevOpsDays roles that roll up to it |
|---|---|
| **Program** | Talk Proposals, Ignite Proposals, Speakers |
| **Logistics** | Venue & Local Logistics, Registration & Invoicing, Evening Event Logistics, Merchandise |
| **Sponsors** | Sponsorships |
| **Marketing** | Website Updates, plus the "Visibility" workstream (section 3.9) |

Credential handling, which the guide treats as a first-class team duty:

> Along with all of these tasks and responsibilities, you'll have to also manage lots of different usernames and passwords for various vendor sites, social media accounts, and so forth. You'll need a way to store all of this securely, centrally, and sanely.
>
> 💡 **Vaultwarden** is an open source credential storage platform that can store usernames, passwords, MFA tokens, and so forth. […] The core organizers run an instance of Vaultwarden that is made _freely available_ to the DevOpsDays organizer community.

Additional named on-site roles, from "Running the event itself":

> - Prepare and share a team playbook of exactly what is scripted to happen when.
>   - Assign one or more MCs to kick off and orchestrate the event
>   - Assign people to introduce specific speakers
> - Consider assigning **"on duty" shifts so one person isn't the SPOF** for all last-minute decision-making in crisis mode

Registration-desk staffing, from "Running registration":

> You may want to staff the registration desk at all times if you want to be able to help attendees with their questions. As the conference organizers may want to attend talks, it's wise to call in favors from friends and family who aren't interested in the subject matter of the talks and won't mind missing them all. **Make sure any such staff have a way of getting ahold of the organizer on duty** for any questions they can't answer on their own.

### 3.5 Timeline template ("Important Dates")

Verbatim from the guide. Note the horizon starts at T-12 months, not T-6, and each
entry carries its own rationale.

> * **T-12 Months to Event:** Kick off venue search, if needed
>   - Why: Venues book out in advance, and in fact, larger venues book out years in advance.
> * **T-10 Months to Event:** Kick off budget discussions
>   - Why: Helps determine sponsorships (and the cost for each) needed and the ticket price.
> * **T-9.5 Months to Event:** Pick venue
>   - Why: See above, but its good to get this locked in.
> * **T-9 Months to Event:** Confirm organizers
>   - Why: Start formulating and start distributing the work
> * **T-8 Months to Event:** Start org dinner
>   - Why: "Breaking bread" with your fellow organizers is a good way to kick things off. Organizing will have its ups and downs, start it off strong.
> * **T-8 Months to Event:** Ensure sponsor prospectus goes out.
>   - Why: Sponsors, especially larger companies, lock in budgets the financial year prior. It is best to get on their radar now instead of after your program has gone live.
> * **T-7.5 Months to Event:** Ensure CFP goes out
>   - Why: If you're trying to draw in the most content possible, having your CFP open for maximum duration draws the most abstracts.
> * **T-7.5 Months to Event:** Kick off semimonthly meetings
>   - Why: It is good to establish a healthy cadence with check-in points and being able to get visibility on how ticket, sponsorship and submissions are going.
> * **T-7 Months to Event:** Ensure marketing is off and running
>   - Why: Marketing is tricky, especially as a new event in a world where social media is quickly changing.
> * **T-6.5 Months to Event:** Ensure registration opens
>   - Why: The more time the registration is open, the more potential visibility it gets.
> * **T-5 months before Event:** Contribute "sustainability donation"
>   - Why: Once you have started selling tickets, you should have the liquidity to make this donation.
> * **T-4.5 months before Event:** Initiate voting of submissions with the organizers
>   - Why: Certain speakers submit to multiple events, require notice to their employers and/or require (international) travel. Getting voting done, on time, and in advance, allows those individuals to arrange the needful.
> * **T-3.5 months before Event:** Launch the program
>   - Why: Your program absolutely drives visibility of your event. Your speakers can help market the event and at the same time would-be buyers might be waiting on your program before purchasing a ticket.
> * **T-3.5 months before Event:** Ensure early bird closes
>   - Why: Often paired with launching the program, you should close early bird.
> * **One Month before Event:** Check on volunteers
>   - Why: The team has been organizing, but you might need day of volunteers to help out. Check with your friends, family, colleagues, meetup participants, etc to see who can help in exchange for access to the event.
> * **Month of Event:** Host
>   - Why: Time to review the Running the event itself section for some guidance on the days of. GOOD LUCK, YOU GOT THIS!

Additional dated constraints stated elsewhere in the guide:

- **CFP window:** "People will usually need at least 4-6 weeks to arrange for travel or time off, and you'll want your call to be open for at least a month, and you'll want at least 2 weeks to consider proposals and fill in any gaps. This means that you should open your CFP as soon as possible, and **close it at least 6-8 weeks before your event**."
- **Catering deadline:** "The catering deadline (by which time you'll need to provide numbers) is usually **a couple weeks or so before your event**."
- **Hotel group rate:** "the group rate usually expires **a month or so before an event**."
- **Merch lead time:** "If you're ordering shirts a few weeks before your event, consider **padding the counts by up to 30% of each size/style**."

### 3.6 Budget line items and sponsor cost ranges

Income and expense categories, verbatim:

> ### Income Categories:
> - **Sponsors**: Sponsorships can constitute a significant portion of your income—**potentially up to 75%**, depending on the sponsorship levels you establish.
> - **Registrations**: Price your registrations to cover the per-attendee costs.
>
> ### Expense Categories:
> - **Venue**: Cost of the location for talks and open space discussions.
> - **Internet**: Provisioning internet access for attendees.
> - **Media**: Costs for live streaming, recording, and captioning talks.
> - **Catering**: Expenses for breakfast, coffee breaks, and lunches. Note that some venues might mandate using their catering services.
> - **Evening Event**: Any activities or gatherings planned for the evening.
> - **Merchandise**: Costs for T-shirts and other promotional items.
> - **Badges & Lanyards**: Essential for attendee identification.
> - **Signage**: Directional and informational signs for the event.
> - **Speaker Expenses**: Hosting a speakers' dinner and small appreciation gifts.
> - **Administrative Costs**: Insurance, taxes, and payment for accounting services.
> - **Sustainability Donation**: Cost of a full price ticket.

**Published sponsor tier pricing** — the only hard currency figures in any of the
four sources:

> - Host (cost of venue): if a company sponsors the venue/food they will be acknowledged as a Host sponsor. Their logo will be directly visible on the main event page. They also have the opportunity to do a pre/post event meetup that will get promoted.
> - **Gold (around 5000 Euro/USD)**: 6 included tickets + a 'promo' spot during talk intermissions + the ability to have a simple table/sponsor presence at the venue.
> - **Silver (around 3000 Euro/USD)**: 4 included tickets, sometimes half a table depending on the local event's choices, sometimes just a single shared swag table.
> - **Bronze (around 1000 Euro/USD)**: 2 included tickets, sometimes can leave stickers/flyers/etc in public spaces
> - **Community Sponsor**: get logo on the site and acknowledgement on social media. Used for media outlets and other conferences that are interested in cross-promotion with you. Sometimes they'll provide giveaways; usually you will not ask them to provide cash.

Named add-on inventory: "A lanyard sponsor / A captioning sponsor / An evening
event sponsor / A lunch or breaks sponsor".

Sponsorship-to-expense ratio target:

> Unless you've got a really strong audience and a fairly guaranteed attendance, you probably want to have **80% or more of your expected expenses covered by sponsors** rather than ticket sales.

Ticket pricing benchmark:

> We recommend charging a minimal fee. This will keep your event accessible by making it cost a fraction of a typical high-priced conference ticket (**perhaps 10% to 20% of what someone might pay** to attend a commercial tech event in your region).

### 3.7 The Good/Better/Best tiered budget

> First, a recommendation: Have a tiered budget for a Good, Better, Best. A Good version of your conference has the bare minimum. Maybe you don't have food and send people out for a long lunch break, saving money on the food portion. Maybe you don't do swag, or have pared-down badges. Whatever is a minimum viable event for you, have that planned. Then have a Better version that costs a bit more but has those nice to haves. Then have a Best version where you can add the fun things that make your event unique (e.g., a few years in Austin had a mariachi band come in for lunch) and start handing away tickets for free.
>
> However you set up that tiered system for your event, **have some go/no-go dates in mind for deciding when you can do each one**. A Good vs Better event call might come in the month leading up to your event when you evaluate how much sponsorship money you have gotten in. […] If you set yourself up this way, you know you can put on a good event for the community regardless of how many people actually come, **avoiding the need to cancel**.

### 3.8 Venue and room-count specifications

Attendee ranges and room sizing, verbatim:

> - A (big) room where everybody can sit comfortably and listen to the talks. This of course depends on the number of attendees you expect. **Events have ranged from 70 to 700 people; a typical first-year event is often around 250 people.** Assess the numbers usually attending your best-attended local meetups; you might get 2-3x that.
> - A number of break-out rooms for the afternoon sessions:
>   - it's nice to be able to put the chairs in a circle for better discussions
>   - you can be creative by splitting the big room in smaller rooms but in practice, separate rooms are less noisy
>   - **we usually go for a few smaller (10-20) and few bigger (20-40) rooms**
>   - it's helpful if the rooms are close to one another, making it easier to move between open space rooms.
>   - you can use the big room for open space too
> - Room to hang out: not everybody attends sessions, and some are more interested in the hallway track. If there is some room for the food or a quiet room that's a plus.
> - Sponsor space: Gold sponsors (at a minimum) get a table to have a presence. Make sure they have a nice spot at the event (typically close to the food or hangout space).

Technical venue qualification questions:

> - Is the venue easily reachable by public transit and/or does it have sufficient parking, depending on the transit options in your local area?
> - Are there (affordable) hotel accommodations nearby? (Running the event in a hotel makes it easy for out-of-town guests.)
> - Does the venue allow for catering by other parties, or what are the options for food?
> - **Does the venue have enough wifi/internet capacity, or can more be added?** Attendees will likely expect it.
> - **Can the video be streamed with enough capacity** (if livestreaming is an option)?

Load-in and commitment cautions:

> Don't overcommit on the number of people coming and don't do a pre-payment for the venue until you must. The same goes for food: it's always easier to add a few extra plates as opposed to having too much food ordered.

> Make sure you ask the venue **how soon sponsors can start shipping items there**, get the correct address/routing info, and ask what fees they might incur. **Find out exact times you'll have access to your space, and find out whether you'll have secure overnight storage** (because both you and definitely the sponsors will need that).

> Venue sponsors (especially if you're in their facility) may try to set limits on other sponsors; try to clarify this in writing ahead of time.

Hotel room-block risk:

> If you're not using the hotel's meeting rooms and catering, they may want you to **guarantee at least 80% or so of the room nights you block off** for your group will be used. This isn't as risky as it sounds if you want to start with a very small block (5 rooms or so, for the night before day one and the night between day one and day two - don't expect people to stay overnight the evening of day two).

Insurance requirement, stated in "Venue logistics":

> Your venue may require some form of insurance. See what they require, and look into something like **TULIP event insurance** depending on what's available for your local area.

### 3.9 Program format and run-of-show

> The recommended format includes:
>
> - talks in the morning: this follows the traditional format of a speaker or panel
> - There is usually an **introduction of about 15 minutes** at the beginning of the conference from the organizers
> - We find that **talks of about 30 minutes** have the right balance for content.
> - You'll want to **let the Gold sponsors speak for a minute between the 30-minute talks as that gives presenters time to set up their laptops**
> - allow for rest and discussion breaks
> - You may break for lunch before the Ignite talks if that works best for your schedule.
> - You'll have a set of several ignite talks: **5 minute talks with 20 slides that auto-advance**
> - openspaces in the afternoon: a self-organizing part where everybody gets to propose a session

> Events usually have **4 30-min talks per day + ignite talks**. Open space sessions are scheduled during the conference, not ahead of time.

### 3.10 Ignite tech-check protocol and backup procedures

This is the most technically specific AV runbook published by any of the four
sources. Verbatim from "Running Ignites":

> Running Ignites can be a challenge: people tend to submit them last minute, or they didn't understand the format too well. Here are a few tips on making this process run more smoothly:
>
> - **Require the Ignite presenters to send the slides ahead of time**
> - Inform the Ignite presenters that there are no presenter notes during their talks
> - **Animations (gifs or slide transitions) and videos may not work due to the conversion process**
> - **PDF is the easiest format to collect all presentations**
>   - An option is to use a Dropbox shared directory
> - You can run either :
>   - `impressive -a 15` [http://impressive.sourceforge.net/](http://impressive.sourceforge.net/)
>   - Adobe Acrobat Reader in [auto-advance mode](http://malektips.com/adobe_reader_7_0019.html); **ask presenters to add empty slide to the end as Reader doesn't exit after the last slide**
> - **Don't let them run on their own laptops**
> - **Use a dedicated laptop (avoid any popups etc...)**
> - Mention again on the day itself.
>   - "Just so you know, your slides will auto advance every 15 seconds; you can't advance them yourself"
>   - Remind the presenters again that there are no presenter notes
> - Have Ignite presenters queue next to the stage and either:
>   - start the slidedeck for them.
>   - or even build all slides in Slidedeck and build in a bio slide as a interludium and have that autoadvance as well

Speaker-wrangling backup, from the speaker section of the guide:

> Even if you've sent these details, pay attention to getting your speakers to the right place at the right time. Keep an eye on whether they have check in at all, and **have a volunteer meet/find them during the previous talk**. Then you can fix last minute issues, and make sure they are ready at the stage at the start of their slot. **If things don't work out, it'll make sure you know before their start time.**

Recording and streaming:

> Whether or not you're able to livestream, **it's important to record all the talks**. This is invaluable for your speakers, and it's great for the community. Your audiovisual company should be able to provide a camera or cameras and **record the feed off the board into a computer**. If you have no budget for recording talks, a smartphone is better than nothing.
>
> If you're going to livestream, **rehearse ahead of time, and then assign at least one person to run it during the event**.
>
> - Some events stream directly to YouTube. **Be very careful not to accidentally include any background music, or YouTube will take your stream down.**

### 3.11 Registration flow

Setup requirements, verbatim:

> - require information for each attendee (rather than for the buyer only)
> - ask for employer name (optional) if people want it printed on their badge
> - ask for T-shirt sizes (make sure you offer more than S-M-L-XL "unisex")
> - (in Europe) ask if they require an invoice; if yes ask more details like VAT number if needed
> - ask if they are interested in attending the evening event on the first night (optionally)
> - disable the facebook integration
> - don't allow people to see who is coming
> - set up hidden ticket types for sponsors, organizers, speakers, etc
> - create access codes for hidden ticket types

> *Attendee email or direct-contact information should never be visible on the website or given out to vendors.* We value privacy and do not want attendees to be spammed.

Day-of desk operation:

> Sort the badges ahead of time **alphabetical by last, then first name**. If you separate out the sponsor ones, keep in mind that some people might not realize if they fell into the "sponsor" tickets or a "regular attendee" ticket according to how their company registered them.
>
> **Sort shirts by style and size, and then let attendees just tell you which size they wanted.** If you built in enough margin of error, this won't cause any problems and will be the most efficient way to deal with it, rather than looking up what they ordered.

### 3.12 Attendance forecasting and no-show rates

> We do not recommend making your event free. Experience has taught us that 'free' events come with a cost:
>
> - **about 30-40% of the people 'grabbing' a free ticket don't show up in the end**
> - this makes it harder to plan logistically: how many people will actually show up?
> - people who could have attended are left out because the event appears 'full'

Ticket-sale spike checkpoints, used as go/no-go signals:

> - Did we get a spike during the first ticket sales week?
> - Did we sell a good bit of early bird tickets? What to look for is probably **15% of the expected ticket sales (e.g., of 400, 60 early birds)**.
> - Did the speaker/agenda announcement gain another decent spike (**~10% of expected sales**)?
> - Did we hit about **40-50% of expected ticket sales minus sponsors, speakers, organizers, and volunteers by a month or so out**? […] If you forgot to send emails out or announced your agenda late, you probably are closer to 25-30% at this point.

### 3.13 Financial-controls risk management

> **You cannot announce a date until you know you have a way to handle money.** Realizing too late that you cannot process money has led to rescheduled or canceled events in the past.

> With all of these expenses, your event will likely be handling a lot of money. **All major expenditures should be presented to and approved by your organizing team** to help prevent conflicts of interest and provide oversight. Many organizing teams have implemented a process where individual organizers pay for expenses directly and request reimbursement from event funds. **Reimbursements are only given if one or more additional organizers approve.**

Named fiscal-host options:

> - US Based: Laura from Conference Ops
> - EU Based: Bernd from Netways or Yvo from [Stichting DevOps Foundation](https://devops.foundation/)

Sustainability donation, new in 2025:

> as of 1 January 2025, we are introducing a modest event fee: each time you run an event (generally once per year), you donate the equivalent of **at least one full price attendee ticket to your event** to the global DevOpsDays organisation.

### 3.14 Badge scanning and attendee-data privacy

DevOpsDays takes the strongest published position of the four sources:

> Sponsors will often ask if attendee badges can be scanned. Using QR codes to receive attendee information is quick and efficient for sponsors, but can be problematic for organizers and raise privacy concerns from attendees. **We strongly discourage you from using scannable badges at your event.**

On the UUID method:

> Many conferences use this because it protects attendee data and it also forces sponsors to use specific software or devices for an additional cost (more revenue for the event). However, **this practice violates one of our DevOpsDays rules: we do NOT ever give out or sell lists with contact details of attendees.**

On the encoded-VCF method, if used, these are stated as mandatory:

> - Attendees must be informed that their information will be encoded, including which details (email, phone, etc) will be included.
> - Attendees must be informed of and provided a method to opt-out. This could be done during registration and QR codes not printed on the badges of those who opt out, or you could provide stickers to cover QR codes.
> - Sponsors must be informed that badges may only be scanned with consent from attendees, and you must enforce this in practice.

> Additionally we recommend that **QR codes be printed on the back side of badges and that badges have two points of contact with lanyards** to help ensure that QR codes are only visible when an attendee shares it.

### 3.15 Cancellation runbook

`utilities/docs/cancel-event.md` is a genuine scenario-planning artefact — the
project maintains a documented, version-controlled procedure for pulling an event.

> If you unfortunately need to cancel your event, there are a few changes you should make to get the website updated. **Just deleting the event isn't a great idea; you want people who try to access the URL to know what happened.**

Steps: delete all event pages except `welcome.md`, `contact.md`, `conduct.md`; add
`aliases` so deleted paths 301 to the welcome page instead of 404; clear
`startdate`/`enddate`/`cfp_date_*` and location fields in
`data/events/YYYY-CITY.yml`; set `cancel: "true"` and
`sponsors_accepted: "no"`; reduce `nav_elements` to `contact` and `conduct`.

> First, you will want to update the content to add a notice that you are canceling the event, along with **any other information you want people to know (if you have details about refunds, rescheduling, etc)**

---

## 4. Accessibility, Risk, and Attendee Experience — `mxsasha/lessobviouschecklist`

Substituted for the non-existent "Mozilla Event Checklist". This is the source
python-organizers itself points to, and it carries the ADA, captioning, and
attendee-experience content the task specified. Mozilla's own contribution is
covered in 4.7.

### 4.1 Repository metadata

| Field | Value |
|---|---|
| URL | https://github.com/mxsasha/lessobviouschecklist |
| Published site | https://lessobvious.cc/ |
| Description | "The Less Obvious Conference Checklist" |
| **Last push** | **2024-08-09** |
| `docs/index.md` last commit | 2024-08-09, "Update wording of accessibility for consistency" |
| Stars | 382 |
| Licence | **CC BY-SA 4.0** — reusable with attribution |
| CI | `.github/workflows/linkcheck.yml` |

Key files:
- `docs/index.md` — https://github.com/mxsasha/lessobviouschecklist/blob/main/docs/index.md (176 lines; the main checklist)
- `docs/financial-aid.md` — https://github.com/mxsasha/lessobviouschecklist/blob/main/docs/financial-aid.md (129 lines)
- `AUTHORS.md` — attribution for contributed recommendations

Stated scope:

> This is not a checklist of things you must do in order for your conference to be any good. […] Consider this more as a list of actionable and practical suggestions to help us make better conferences. **You will probably not be able to follow every single suggestion, and that's fine.**

### 4.2 ADA compliance and physical accessibility

The repo cites the ADA checklist directly as its reference standard:

> - [**ADA Checklist for Existing Facilities**](https://www.adachecklist.org/doc/fullchecklist/ada-checklist.pdf) from the [New England ADA center](https://www.adachecklist.org/checklist.html). This is very extensive and aimed more at building owners in general, but highlights many obstacles you might otherwise not think of.
> - [A Checklist for a Successful Accessible Conference](https://www.ifla.org/wp-content/uploads/2019/05/assets/lsn/publications/a_checklist_for_accessbiility_at_library_conferences_rev_2021.pdf) from IFLA.
> - [How to Make Your Events More Accessible and Inclusive](https://splashthat.com/blog/accessible-event-planning) by Cai Charniga.

On the inadequacy of generic compliance language:

> For people with reduced mobility, **be specific about the actual situation**. Some people that use wheelchairs can actually cross a few steps if needed. Some require specific accessible toilets, others do not. **Width and turning radius vary greatly. A generic term like "wheelchair accessible" leaves many questions for these people.** Providing photos is great.

> Some obstacles may not be a major barrier to most wheelchair users, but may be to anyone with other mobility issues or visual impairments, as they can become a **tripping hazard**.

The full operational checklist (verbatim), from "Accessibility":

> - Write an accessibility statement. [PyCon UK](https://2023.pyconuk.org/venue/) and [DjangoCon Europe 2023](https://2023.djangocon.eu/inclusion/) have good examples. In this statement, you inform people with disabilities or impairments what you can offer them, what obstacles may be present, and what alternatives you can provide. The purpose is to inform people what you are planning to do, what you do and don't know, and that you're happy to listen to anyone's questions in this area. [Including photos](https://ep2024.europython.eu/accessibility), especially when the route is a bit tricky, and floor plans is always a great addition.
> - Have the accessibility statement published early on. **If you publish it after early bird pricing closes, you're basically making disabled people pay more.** If you publish it after CFP closes, they are less likely to become speakers.
> - Make sure there is an accessible way to contact you for inquiries, which should probably be email. Forms and too many detailed questions might be inaccessible and/or put people off.
> - Don't assume you know the accessibility needs of your participants, or attempt to guess them. **Do not ask them to provide details of any health conditions** (as opposed to their access needs) as that information is intrusive not useful anyways.
> - Check and document whether things like step-free access doors and lifts can be used independently. Sometimes there is no alternative, but it's very unpleasant when attendees can not navigate the venue independently. If there is no alternative, document it in your statement, make sure staff is available, or provide clear direction on how to contact staff.
> - Make sure paths remain wide enough with furniture, e.g. for people with mobility aids. Even if buildings have step free access, chairs, tables, promotion booths and other obstacles are sometimes placed too close to each other.
> - Don't forget about access to the stage.
> - Sometimes things do not go according to plan, and the situation is not as accessible as people were expecting. Do whatever you can to provide workarounds, and actively inform anyone you know may run into those obstacles.
> - Also check and document the accessibility of social event and dinner venues. **They're actually more likely to have significant issues than an average conference venue.**
> - In signage, lanyard colours and badge design, be mindful of those with reduced colour perception. A good tool to test this on Mac OS X is [Color Oracle](http://www.colororacle.org).
> - Publish details of your health/covid policy. Is masking expected? Required? Vaccinations? Document this clearly and early. **Harassing someone for wearing a mask should always be treated as a CoC violation.**

### 4.3 Live captions, stenography, and ASL

On live captioning (verbatim):

> - Consider having a captioner/stenographer. **This helps a wide range of attendees**: people with hearing issues, speakers with various accents, and allows reading back if someone was distracted. **It also provides a written and searchable record afterwards.**

The checklist does not prescribe an ASL interpreter per event — the operative
recommendation is to publish what access services you provide in the
accessibility statement (4.2) and to be contactable for requests that fall
outside the published menu. DevOpsDays §3.6 confirms captioning is a recognised
sponsorable line item: "Media / A lanyard sponsor / A captioning sponsor".

### 4.4 Quiet rooms and sensory accessibility

Verbatim:

> - Offer a quiet room for people who may feel overwhelmed by the social interactions, sound or light level and business at conferences. A quiet room should be a (somewhat) noise insulated room where there is no talking, to allow attendees a chance to decompress. It's also a good place for people that need to focus on some work. **It should not be a place for online meetings.** All you need is a room with some chairs/desks/beanbags. Make sure that your quiet room is in a place that's easily accessible. **Also make sure there are no flashing or flickering light, and that the brightness level is not too intense.**

### 4.5 Risk management and the Code of Conduct ladder

The CoC ladder here is operational, not legal — the operative artefact for
event liability is still §3.8 (DevOpsDays' TULIP pointer) and §1.10 (CNCF's D&O
cover note). What this checklist adds is the **response-readiness layer** for
behavioural risk.

CoC team composition, verbatim:

> - Your CoC is useless if you can not respond to issues. Set up a CoC team. **An ideal size for this is four people.** These people are the primary responsible persons for dealing with any reports, and should be able to have their hands free at any time. They can involve other team members if needed, but having a small team makes it easier to respond consistently, professionally and timely, without distracting the rest of the organizing team.
> - Make sure the members of the team are known and listed by name on the website.
> - **Have special phone numbers available for reporting CoC issues, especially for emergencies.** Often people buy prepaid sim cards in the country of the conference, and put these in cheap non-smartphones. One or two members of the team carry these the entire conference. The numbers are on posters, the conference booklet and the website, and their availability is mentioned in the opening notes.
> - The primary reporting mechanism is probably still email, so have a conduct@yourconference.com available and communicated that goes to the team. **Don't ask people to report to a wider group than the team.**
> - If you have a chat or a hashtag, don't forget to monitor those for CoC issues. Consider also using [highlight words](https://get.slack.help/hc/en-us/articles/201398467-Highlight-word-notifications) to notify your team when an abusive term is used, or when someone starts a conversation about harassment or the Code of Conduct.

Enforcement escalation, verbatim:

> - You or your community may be hesitant to adopt a CoC, for example because it feels to some as a tool of censorship. Issues where someone's behaviour is so unacceptable that they are removed from the conference, or even the community, do occur, and it's essential that you are able to handle them. However, many issues are much less serious, and more due to someone being unaware than of ill will. They still require careful handling, but that could also be a serious conversation of "you did this, this isn't cool, don't do it again, have a nice conference".

Transparency and reporting low-friction, verbatim:

> - To build further support of a CoC, publish a transparency report afterwards. We first [published one for DjangoCon Europe 2018](https://2018.djangocon.eu/news/coc-transparency/). Ensure nobody in there is identifiable (this applies to both the perpetrator, the target if there is one, and anyone else involved).
> - Do not underestimate the energy it will take from the CoC team to deal with issues.
> - Never assume you don't need a CoC because nobody reported any issues, and therefore you don't need one. **It can takes time for people to feel comfortable to report issues.** And not having a CoC at all is sending a very strong message to everyone that reporting isn't worthwhile.
> - Keep the barrier for reporting as low as possible. This means people should not be afraid to report, and have to feel that reporting is safe. When I introduce the CoC in a conference opening, I always stress that "I feel uncomfortable about what happened" is enough to contact the team, and **that we will not punish people if it turns out not to be a CoC violation**.
> - For more about CoC enforcement, see this [overview of CoC warning signs](https://otter.technology/blog/2017/12/28/code-of-conduct-enforcement-warning-signs/) by Sage Sharp.

Cross-reference: §3.14 (DevOpsDays' UUID/QR posture) addresses a related but
distinct risk vector — the *privacy* risk of badge scanning. The two together
(behavioural risk from §4.5, data risk from §3.14) are the full attendee-trust
surface that these four sources cover.

### 4.6 Attendee experience: registration, wayfinding, name handling

**Registration flow** — the substantive list, verbatim from "Tickets":

> - If you have a limited amount of tickets and expect to sell out quickly, **limit the number of tickets per purchase**. That'll give everyone a fair chance, and help get a mixed group of attendees, instead of a small number of companies buying out all the tickets.
> - When deciding when to open ticket sales, **consider different time zones**. 11:00 in Europe means Americans would have to wake up in the night to get tickets. **15:00 UTC often works fairly well for Europe and America**, but not as good for Asia. You can sell in multiple batches at different times of day to give people from either region a chance.
> - If you think you might sell out, set up a waiting list. You could send any cancelled tickets here, and refund the person that needed to cancel.
> - If your tickets tend to sell out very fast, **you could use a lottery instead**. People can enter during an entire week, and you randomly select winners that then have one week to register and pay for their ticket. Any remaining tickets go back into the lottery. **This promotes inclusivity and diversity, because if people only have a few specific minutes or hours to get their ticket, it's easy for people with desk jobs, but might be impossible for those with other kinds of work or other responsibilities (e.g. parents).**
> - **Don't sell all your tickets right away.** Keep a small batch (5-10 or so) for unforeseen situations. You can always decide to sell them as last-minute tickets later.
> - If you have any side events, like a sprint, ask people in the ticket whether they will attend. That'll get you some attendance numbers early on. Make sure people who are not familiar with sprints or another event can easily find what they are about.
> - Under [no circumstances use PayPal](https://daniel.feldroy.com/posts/we-are-not-using-paypal) for receiving payments. **In general, be careful with who you give control over your funds. Get it to your own bank account as soon as possible.**
> - Consider using a specialised ticket sales service. Organisers in the Python and Django community have had good experiences with [Pretix](https://www.pretix.eu/) and [Tito](https://ti.to).
> - Do not ask people to bring an government ID that matches their ticket. Some people, including many trans people, are unable to obtain a government ID in their correct name. **Even if you are more flexible in practice, having this as a general policy is exclusionary.** If you'd like more security at your registration desk, offer the choice of bringing either a government ID with name matching ticket, or showing a print/screenshot of the ticket. Be clear that people can choose either option.

Cross-reference to the more technical registration-desk flow in §3.11
(DevOpsDays): badge sorting, employer-on-badge opt-in, VAT fields, hidden
ticket types, attendee-list opt-in.

**Wayfinding and on-site signage** — verbatim from "Accessibility":

> - Plan for signs to guide people without overwhelming them. Design them well ahead with a consistent color scheme and the conference logo. Depending on your venue layout, it can be worth it to invest in stands to place them in the best position, rather than stick them to a wall. **If there are separate accessible paths or toilets, have signs for those as well.**
> - Earlier in the conference, **have some extra volunteers around to guide people**. That will also help you discover where you need to fix up your signage.

Cross-references: §1.5 (CNCF's "label the way to restrooms, the elevator,
terrace" / "label 'restricted' areas" list), §3.8 (DevOpsDays' A/V cabling and
break-out room adjacency notes).

**Name handling on badges** — verbatim from "Inclusivity":

> - Whenever you ask for people's names, **don't ask for a first and last name**. Not everyone has a clear first and last name, and there is little reason to want to separate them. When you ask for names, **ask how they would like to be called in a single field**. If needed, add a separate field for their legal name. You'll probably need the latter if you are making hotel reservations for people, for example.

And from "Other":

> - If you are making badges, make sure the names are very visible. It's not uncommon for conferences to print them no larger 14pt or so, which makes them impossible to read from any distance. Ideally, print them double sided as they tend to flip around.
> - **Make sure that the name of all participants is printed correctly on the badges.** When using a decorative font, make sure it has support for a wide range of non-ascii characters. If the name of a participant doesn't render correctly, don't try and shorten or otherwise alter their name without asking them first.
> - Provide buttons or stickers for pronouns, including at least **"He/Him/His", "She/Her/Hers", "They/Them/Theirs" and "Other/blank"**.
> - Always make a bunch extra blank badges and posters, so that you can make some on the spot if needed.

**Welcoming the room** — verbatim from "Making attendees feel at home":

> - In general, use all your communication to make attendees feel welcome. At Django Under The Hood, we had posters with "Yay, you made it!" on all the entrances. Even [minor touches like that](https://archive.is/0RkSa) can help create a good atmosphere at your conference. It's simple but really makes a difference in the vibe.
> - Basic bathroom supplies are much harder to find in an unknown country and area. At DUTH 2015 and [DjangoCon Europe 2016](https://archive.is/8sG1n) there were boxes near the bathrooms with items like toothbrushes and hygiene products, free to take as needed by all attendees. It makes people feel more welcome, and provides a lot of benefit for little effort.
> - Make sure the organisers are visible. If you have a registration desk, try to have someone there all the time. If an attendee needs help, it can make them feel very lost if they can't find an organiser.
> - Discourage clique forming, and make first-timers feel much more welcome, by encouraging your attendees to follow the [Community++ rule](http://ericholscher.com/blog/2017/dec/2/breaking-cliques-at-events/) and the [Pac-Man rule](http://ericholscher.com/blog/2017/aug/2/pacman-rule-conferences/#pac-man-rule).

**Local travel information** — verbatim:

> - The city where you're holding your conference is probably well known to you. This is not the case for most of your visitors. Help your attendees find their way around by writing something about travelling to and around the conference. [Here's what I wrote for Django Under the Hood](http://2016.djangounderthehood.com/travel/). Which airport should people go to? How do they best get to the city? How do they get from hotels to the venue? Can I buy transit tickets with a credit card? Do I need a visa? Is there a nearby supermarket?
> - **Check local news for local events, construction sites or weather warnings** that might impact the attendees' travel to the venue. Communicate these to your attendees to help them navigate it.

### 4.7 Feedback mechanisms and post-event transparency

The strongest attendee-experience close-out loop is the CoC transparency report,
already quoted in §4.5. On the broader feedback surface, this checklist is
sparser than DevOpsDays §3.10 (which quotes CNCF's QR-coded survey slide) but
offers:

- **CoC transparency reports** (4.5): published within weeks of the event,
  redaction of all parties, used as a deterrent and accountability artefact.
- **Conference-specific Slack** that is decommissioned after the event: "Set
  up a place for your attendees to connect, like Slack. Make it specific to one
  edition of your conference, so that you can remove it some time after. **It's
  not a great idea to keep it running, because you stay responsible for Code of
  Conduct incidents.**"
- **Recording moderation**: "If you are uploading talk recordings to services
  like YouTube that allow comments on videos, ensure the comments are moderated
  or disabled. Otherwise, you risk [harassing comments being made]
  (https://2016.djangocon.us/blog/2016/08/31/code-conduct-transparency-report-youtube-comments/),
  at any time after the conference, when your team is also probably less
  available."

Mozilla's own (small) contribution: the `mozilla/inclusion` repo, referenced
in the Sourcing Corrections table, publishes CoC enforcement laddering —
the document trail that pairs with the response team described in §4.5.

### 4.8 Financial aid: principles that double as accessibility

The `financial-aid.md` companion document is not just a travel-grant guide — it
operates as a participation-accessibility checklist. Direct applicability to
the accessibility frame of this section:

> - **Asking for help is hard.** […] With it being easy for people to feel
>   discomfort and insecurity about applying, it's important that we put extra
>   effort into ensuring everyone feels welcome to apply.
> - **Be extremely explicit in who you are targeting.** The default
>   "underrepresented group in tech" sentence leaves refugees, caregivers,
>   neurodiverse people, and others unsure whether they qualify.
> - **Be mindful of excluding people with your requirements.** Mandating
>   same-gender room-shares excludes neurodiverse attendees who need private
>   space and creates problems for non-binary attendees. Suggest sharing; don't
>   require it.
> - **Never ask people which underrepresented group they belong to.** Doing so
>   forces disclosure that can be dangerous or shameful and cannot be screened
>   for anyway.
> - **On timing.** Announce results on time, and refund against proof of
>   booking — never require an aid recipient to commit non-refundable costs
>   before they know the grant is confirmed.

Cross-reference: §1.9 (CNCF's published 6-8 week notification deadline and
30-day reimbursement window) and §3.13 (DevOpsDays' named fiscal hosts) for
the operational counterpart.

---

## 5. Synthesis: How the four sources fit together

The four repos do not duplicate one another — each owns a different operational
slice, and the gap map is what an event operator needs in order to use them
together.

### 5.1 Comparative ownership matrix

| Operational concern | Primary source | Secondary / corroborating | Gap |
|---|---|---|---|
| Event-tier definitions, attendee caps, show-rate maths | §1 CNCF | §3 DevOpsDays | KubeCon itself has no published tier table |
| **Venue requirements** (load-in, F&B, Wi-Fi, wayfinding) | §1.5 CNCF (checklist) | §3.8 DevOpsDays (technical qualification Qs) | None — strongest joint coverage |
| **AV rider / decibel targets / console specs** | — | — | **No source publishes.** Operational gap |
| Speaker management workflow | §1.7 CNCF | §3.10 DevOpsDays (Ignite tech-check) | §4 covers the speaker gift + pronoun/intro ritual side |
| CFP tooling list | §2.4 python-organizers | §3.5 DevOpsDays (CFP-window rules) | Both recommend pretalx/Pretix without endorsing either absolutely |
| **Budget line items + sponsor tiers in currency** | §3.6 DevOpsDays | — | Only source with hard numbers |
| Timeline template | §3.5 DevOpsDays (T-12mo) | §1.9 CNCF (T-6mo scholarship launch) | §1 is narrower; §3 is the spine |
| **Insurance (event liability / D&O)** | §3.8 DevOpsDays (TULIP pointer) | §1.10 CNCF (D&O for LF volunteers) | Both are pointers, not policies |
| **Travel funding / financial aid timeline** | §1.9 CNCF | §4.8 (lessobviouschecklist) | §4 adds the *who/why*, §1 adds the *when* |
| **Date conflict checking** | §2.6 python-organizers (`conferences` CSV, 2017-2028) | §2.2 (religious-holiday interfaith list in lessobviouschecklist) | — |
| **Cancellation / no-show runbook** | §3.15 DevOpsDays (versioned) | §3.12 (no-show rate maths) | §3 is the only source with a real cancel-event.md |
| **Registration flow** | §3.11 DevOpsDays (technical) | §4.6 (inclusion-aware: lottery, no-PayPal, no-ID-matching) | §3 covers plumbing, §4 covers policy |
| **Wayfinding and signage** | §4.6 (inclusivity-aware) | §1.5 CNCF (label-restricted-areas) | — |
| **ADA / physical accessibility** | §4.2 (lessobviouschecklist, ADA-checklist PDF cited) | — | Single-source; should be paired with venue walkthrough |
| **Live captions / stenography** | §4.3 (recommends captioner) | §3.6 (captioning is a sponsorable line item) | No source quantifies captioning cost |
| **ASL interpretation** | §4.3 (implicit via accessibility statement) | — | **No source publishes a workflow.** Operational gap |
| **Code of Conduct — design** | §3.3 DevOpsDays (mandatory) | §2.4 (hotline tooling) | — |
| **Code of Conduct — enforcement / response** | §4.5 (lessobviouschecklist, 4-person team + prepaid SIM) | §3.3 DevOpsDays | §4 is the most detailed on response readiness |
| **Attendee data privacy / badge scanning** | §3.14 DevOpsDays (strongest published position) | — | Single-source; rest is silent |
| **Feedback / transparency reporting** | §4.5 (CoC transparency report) | §1.7 (QR-coded survey slide) | §4 publishes the artefact; §1 publishes the trigger |
| **Welcome / anti-clique culture** | §4.6 (Pac-Man rule, Community++ rule) | — | Single-source |
| **Sustainability / footprint** | §4 (lessobviouschecklist, "Footprint" section) | §3.6 (sustainability donation as budget line) | §4 is prescriptive; §3 is financial |

### 5.2 Synthesis recommendations for downstream readers

If you are using this document as input to a single consolidated event-ops
runbook, the four sources map cleanly onto three derived rules:

1. **Use §1 (CNCF) and §3 (DevOpsDays) as the operational spine** for tier
   definitions, timeline, budget, registration plumbing, and cancellation
   scenario. These are the two sources with current, dated content (last push
   June-August 2026).
2. **Use §4 (lessobviouschecklist) as the accessibility and culture overlay.**
   §4 owns the ADA, captions, ASL-via-statement, name-handling, pronoun, and
   CoC-enforcement detail that the other three sources either touch lightly
   (DevOpsDays §3.14) or do not mention at all (CNCF, python-organizers).
3. **Use §2 (python-organizers) only for the `conferences` date-conflict CSV
   and the CFP-tooling menu.** The `resources` repo's `???` placeholders are
   not load-bearing; the only durable extract from it is the video-licensing
   warning (§2.3) and the Less-Obvious-Checklist onward pointer (§2.5).

**Three operational gaps remain across all four sources** and must be filled
from non-open material (vendor AV riders, legal counsel, accessibility
specialists):

- **AV rider templates, decibel targets, console/PA specifications.** No open
  repo publishes them. A live-sound engineer and a venue contract are the
  substitutes.
- **ASL interpretation workflow.** §4.3 covers the principle (publish what you
  provide; be contactable for what you don't); none of the four sources
  publishes a request-intake form, a provider-shortlist, or a budget range.
- **General-liability event insurance policy text.** §3.8 names TULIP as a US
  starting point; §1.10 names D&O cover for LF volunteers. Neither is a
  general-liability policy that a venue will accept. A broker is required.

### 5.3 Provenance and reusability summary

| Source | Last push | Licence | Reusable in your docs? |
|---|---|---|---|
| `cncf/communitygroups`, `cncf/foundation` | 2026-06-10 / 2026-08-07 | LICENSE present (per-file); CNCF governance defaults | Yes with attribution to CNCF |
| `python-organizers/resources` | 2020-10-01 | NOASSERTION | Cite verbatim with attribution; do not assume permissiveness beyond fair use |
| `python-organizers/conferences` | 2026-08-08 | (data) | CSV is load-bearing for date-conflict checks |
| `devopsdays/devopsdays-web` | 2026-08-07 | Per-page CC-BY-SA where marked | Yes with attribution |
| `mxsasha/lessobviouschecklist` | 2024-08-09 | **CC BY-SA 4.0** | Yes with attribution + share-alike |

This document quotes from all five under fair-use / open-licence terms as
indicated. Verification snapshot against the GitHub API: 2026-08-11.
