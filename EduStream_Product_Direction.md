# EduStream --- Product Direction & Development Plan

## Purpose

This document is the strategic source of truth for the future direction
of EduStream.

EduStream should not be treated as merely a video-streaming website,
LMS, or course aggregator. The central product thesis is:

> **EduStream is a social operating system for completing courses.**

The core problem is not that students cannot find educational content.
There is already an enormous amount of content on YouTube, Telegram,
MOOCs, blogs, papers, and elsewhere.

The problem is:

-   students start courses and do not finish them;
-   learning is isolated;
-   educational content competes against highly social entertainment;
-   students lack visible accountability;
-   it is difficult to discover what other people are learning;
-   finding peers studying the same material is difficult;
-   scattered videos do not feel like a coherent course.

EduStream should make learning itself social and visible.

------------------------------------------------------------------------

# 1. Product Vision

## Core statement

> **Study together. Finish together.**

Or, internally:

> **Make learning socially visible, while keeping the social layer
> focused on learning rather than distraction.**

The product should create the feeling:

> "Other people are studying this right now, so I should study too."

This is the fundamental behavioral loop.

A user should open EduStream and immediately understand:

-   What am I learning?
-   What should I continue?
-   Who else is learning it?
-   What is trending?
-   Who is studying right now?
-   What have my friends completed?
-   What should I read/watch next?
-   Can I study with someone?

------------------------------------------------------------------------

# 2. Product Thesis

Traditional learning platforms optimize primarily for content delivery.

Social networks optimize for social interaction.

EduStream should combine the useful parts of both:

``` text
Educational Content
        +
Course Structure
        +
Progress
        +
Social Presence
        +
Peer Accountability
        +
Discussion
        +
Knowledge Sharing
        +
AI Assistance
        =
Social Learning Operating System
```

The key difference is that social interaction should reinforce learning
rather than become another source of distraction.

## Important principle

Avoid:

``` text
Study
→ feed
→ random content
→ notifications
→ endless scrolling
→ lost time
```

Prefer:

``` text
Study
→ see peers studying
→ join a study session
→ discuss a concept
→ return to lecture
→ complete lecture
→ progress
```

The product should provide **social presence without social-media-style
distraction**.

------------------------------------------------------------------------

# 3. Core Product Loop

The ideal user loop is:

``` text
Discover a course
        ↓
Join / save course
        ↓
See other people learning it
        ↓
Start learning
        ↓
See peer activity
        ↓
Study together / chat
        ↓
Complete lecture
        ↓
Gain progress / XP
        ↓
Return because friends are progressing
        ↓
Finish course
        ↓
Write notes / blog / discussion
        ↓
Help another learner
        ↓
Attract more learners
```

This creates a network effect around learning rather than posting.

------------------------------------------------------------------------

# 4. The Homepage Should Feel Like a Learning Feed

Do not make the homepage simply:

> "Here are some courses."

It should feel like a live learning environment.

Possible sections:

## Continue Learning

``` text
General Relativity
████████████░ 83%

Carroll — Chapter 7
Continue →
```

## 🔥 Trending Courses

Examples:

``` text
MIT Linear Algebra
2,341 learners

Stanford CS229
1,820 learners

Deep Learning Specialization
1,294 learners
```

Trending should be based on actual learning activity, not just clicks.

Potential metrics:

-   new learners;
-   active learners;
-   completion velocity;
-   recent watch activity;
-   course growth;
-   discussion activity.

## 🟢 People Studying Now

Example:

``` text
17 people are learning Physics

Rahul     General Relativity     42 min
Priya     Quantum Mechanics     31 min
Aman      Linear Algebra        18 min

[Study Together]
```

This is one of the most important features.

The product should make "studying" analogous to the "online" indicator
on social platforms.

------------------------------------------------------------------------

# 5. Social Presence

A user's profile should communicate learning activity.

Example:

``` text
Vaibhav

🟢 Studying
General Relativity
42 min

🔥 7 day streak

Current course
████████████░ 83%

Courses completed
17

Currently learning
Carroll — Chapter 7
```

Possible social states:

-   Online
-   Studying
-   Taking a break
-   Offline

The primary useful status is:

> 🟢 Studying

This creates ambient accountability without requiring conversation.

------------------------------------------------------------------------

# 6. Friends and Course Groups

Global leaderboards are less useful than small social groups.

A user probably cares more about:

> "I am #2 among my five friends."

than:

> "I am #18,421 globally."

Build private course groups.

Example:

``` text
GR Study Group

Vaibhav    ███████████░ 78%
Aman       ██████████░░ 71%
Rohit      ███████░░░░░ 52%
Priya      ████████████ 85%
```

Group milestones:

``` text
Next milestone:
Complete Chapter 8 by Friday
```

This creates accountability and competition without making the entire
product a game.

------------------------------------------------------------------------

# 7. Nearby / Campus Learning

"People nearby" is potentially a strong differentiator.

However, never expose exact user location.

Use privacy-preserving concepts:

-   city;
-   university/campus;
-   broad region;
-   optional visibility;
-   approximate nearby learner counts.

Example:

``` text
IIT Kanpur
1,248 learners

Physics
27 studying

General Relativity
8 online now
```

The most useful implementation may be campus-based communities:

``` text
IIT Kanpur → Physics → General Relativity
```

Users should explicitly opt into campus/location visibility.

------------------------------------------------------------------------

# 8. Course Import Is a Core Differentiator

EduStream should allow users to turn scattered video sources into
structured courses.

Possible sources:

-   YouTube playlists;
-   Telegram channels;
-   authorized video sources;
-   uploaded/private material;
-   eventually other supported sources.

Example:

``` text
+ Add Course

YouTube playlist
Telegram channel
Video collection
```

Then:

``` text
Detected 83 videos

12 modules
83 lectures
41h 32m estimated duration
```

The system should organize:

``` text
Course
 ├── Module
 │    ├── Lecture
 │    ├── Lecture
 │    └── Lecture
 ├── Module
 └── Module
```

This converts chaotic content into an LMS-like experience without
requiring EduStream to own the original content.

------------------------------------------------------------------------

# 9. AI Course Builder

Long-term, an imported course should be automatically enriched.

Potential pipeline:

``` text
Videos
 ↓
Transcription
 ↓
Topic extraction
 ↓
Module detection
 ↓
Prerequisite detection
 ↓
Summaries
 ↓
Quiz generation
 ↓
Course graph
```

Example:

``` text
Quantum Mechanics

Module 1 — Linear Algebra
Module 2 — Hilbert Spaces
Module 3 — Operators
Module 4 — Quantum States
Module 5 — Measurement
```

The AI should help organize content, not replace the learning
experience.

------------------------------------------------------------------------

# 10. Learning Layer

The minimum learning system should include:

-   video progress;
-   resume position;
-   lecture completion;
-   module completion;
-   course completion;
-   watch history;
-   notes;
-   bookmarks;
-   transcripts;
-   discussions.

Next layer:

-   quizzes;
-   checkpoints;
-   revision;
-   spaced repetition;
-   prerequisite tracking.

The key distinction is:

> Do not measure only whether the user watched something.

Eventually measure whether the user learned it.

------------------------------------------------------------------------

# 11. Gamification

Gamification should reward useful learning behavior.

Avoid making raw watch time the primary metric.

Bad:

``` text
10 hours of video = huge score
```

because users can simply leave videos running.

Better:

``` text
Complete lecture       +10 XP
Complete module        +50 XP
Pass quiz              +30 XP
Complete course        +500 XP
Maintain streak        +100 XP
Help peer              +20 XP
Answer discussion      +15 XP
Complete weekly goal   +100 XP
```

Potential achievements:

-   First course completed
-   7-day streak
-   100 lectures completed
-   Helped 10 learners
-   First study group
-   Completed a difficult course

------------------------------------------------------------------------

# 12. Leaderboards

Use multiple leaderboard types.

## Friend leaderboard

Most important.

## Course leaderboard

Who is progressing through this course?

## Group leaderboard

Who is progressing fastest within a study group?

## Campus leaderboard

Optional, depending on privacy and community size.

## Global leaderboard

Useful eventually, but not the primary social mechanism.

Leaderboard rankings should reward learning behavior, not passive video
playback.

------------------------------------------------------------------------

# 13. Study Together

This is a flagship feature.

Users watching the same course/lecture should be able to join a
synchronized session.

Possible features:

-   synchronized playback;
-   pause/play synchronization;
-   participant list;
-   group chat;
-   shared timestamps;
-   reactions;
-   optional voice/video later;
-   shared notes;
-   session progress.

Example:

``` text
General Relativity
Chapter 7

🟢 8 studying now

[Join Study Session]
```

The goal is to recreate:

> "We are all studying together in the same room."

without requiring everyone to physically be together.

------------------------------------------------------------------------

# 14. Chat

Chat should be contextual.

Avoid one giant global chat.

Better:

``` text
Course
 └── Module
      └── Lecture
           └── Discussion
```

A user can ask:

> "Why does the lecturer make this approximation at 23:41?"

Others can answer.

Eventually discussions can be linked to exact video timestamps.

Example:

``` text
23:41
Why is this approximation valid?

3 replies
```

This turns lectures into collaborative knowledge objects.

------------------------------------------------------------------------

# 15. Persistent Player

The existing work on persistent/floating/PiP video should remain
central.

The user should be able to:

-   navigate the site;
-   read discussions;
-   browse blogs;
-   inspect notes;
-   chat;

while the lecture continues playing.

The video should feel like the user's persistent "learning session."

The existing work on:

-   persistent player;
-   draggable player;
-   collapsible player;
-   mobile PiP;
-   chat integration;

is therefore strategically aligned with the product vision and should be
preserved.

------------------------------------------------------------------------

# 16. Blogs

Blogs should not be treated as an unrelated blogging platform.

They should be connected to the learning graph.

Example:

``` text
General Relativity

Course
Lectures
Notes
Discussions
Articles
Blogs
Learners
```

A student could write:

> Why Schwarzschild coordinates break down at the horizon

That article can be attached to:

-   General Relativity;
-   Schwarzschild metric;
-   a specific course;
-   a specific lecture;
-   relevant topics.

This creates:

``` text
Video
 ↓
Article
 ↓
Discussion
 ↓
Learners
 ↓
Course
```

Blogs can eventually become a discovery engine for courses.

------------------------------------------------------------------------

# 17. AI Tutor

AI should be contextual to the learning material.

Do not just add a generic chatbot.

Useful features:

## Ask this lecture

> Explain what happened from 23:10--26:40.

## Ask this course

> What prerequisites do I need for Chapter 7?

## Explain

> I don't understand why this approximation is valid.

## Quiz me

> Test me on the last three lectures.

## Revision

> Give me a 10-minute revision of everything I learned this week.

The AI should have access to:

-   transcript;
-   course structure;
-   lecture;
-   notes;
-   user's progress.

------------------------------------------------------------------------

# 18. Knowledge Graph Direction

Long-term, EduStream can become more than a course database.

Think:

``` text
                   General Relativity
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
      Courses          Blogs          Lectures
          │              │              │
          ↓              ↓              ↓
       Students       Discussions      Notes
          │
          ↓
      Study Groups
```

Eventually:

``` text
Topic
 ↓
Prerequisites
 ↓
Courses
 ↓
Lectures
 ↓
Notes
 ↓
People
 ↓
Discussions
 ↓
Blogs
```

This "learning graph" could become the long-term moat.

------------------------------------------------------------------------

# 19. Technical Direction

The current repository has evolved substantially from the initial
Streamlit prototype.

Current broad direction:

``` text
Next.js frontend
       ↓
FastAPI backend
       ↓
Database / persistence
       ↓
Telegram / YouTube / other ingestion
```

The migration to a modern frontend is the correct direction for this
product.

The existing codebase already contains substantial work around:

-   Next.js / React frontend;
-   FastAPI backend;
-   Telegram ingestion;
-   YouTube ingestion;
-   authentication;
-   progress tracking;
-   analytics;
-   AI chat;
-   persistent player;
-   mobile UX;
-   backup/restore;
-   chat;
-   course structure.

Do not rewrite everything again just because the architecture is not
perfect.

Stabilize first.

------------------------------------------------------------------------

# 20. Suggested Production Architecture

Eventually move toward:

``` text
                     Next.js
                       │
                 REST / WebSocket
                       │
                    FastAPI
                       │
        ┌──────────────┼───────────────┐
        ↓              ↓               ↓
     Postgres        Redis           Workers
        │                              │
        │                    ┌─────────┼─────────┐
        │                    ↓         ↓         ↓
        │                 Telegram   YouTube    AI
        │
        ↓
 Courses / Users / Progress /
 Groups / Social / Discussions
```

Potential additional infrastructure:

-   object storage for thumbnails/assets where appropriate;
-   background workers for ingestion/transcription;
-   WebSockets for live sessions;
-   Redis for presence/live activity;
-   Postgres for production relational data;
-   CDN where necessary.

But do not prematurely over-engineer this.

------------------------------------------------------------------------

# 21. MVP / Public Beta Scope

The public beta should NOT contain every future feature.

The minimum compelling product should be:

### Core

-   account;
-   course discovery;
-   course import;
-   structured courses;
-   video playback;
-   progress;
-   resume position.

### Social

-   friends;
-   people studying now;
-   course groups;
-   basic leaderboard;
-   contextual chat;
-   study together.

### Discovery

-   trending courses;
-   currently active learners;
-   topic/category discovery.

### UX

-   persistent player;
-   responsive mobile UI;
-   good navigation;
-   reliable playback.

That is enough to test the thesis.

------------------------------------------------------------------------

# 22. Development Roadmap

## Phase 0 --- Stabilization

Before adding major features:

-   remove major bugs;
-   improve error handling;
-   test authentication;
-   test concurrent users;
-   test video playback;
-   test mobile;
-   clean API contracts;
-   update README;
-   document deployment;
-   add logging;
-   add health checks;
-   secure secrets;
-   verify backup/restore.

Goal:

> A stranger should be able to use the product without your
> intervention.

------------------------------------------------------------------------

## Phase 1 --- Public Beta

Launch to a small student community.

Target:

-   IIT students;
-   university students;
-   serious self-learners;
-   friends/classmates.

Measure:

-   registrations;
-   course imports;
-   first lecture started;
-   first lecture completed;
-   7-day retention;
-   30-day retention;
-   courses completed;
-   study sessions;
-   peer interactions.

Most important metric:

> **Course completion rate among active learners.**

------------------------------------------------------------------------

## Phase 2 --- Social Learning

Build:

-   friends;
-   study status;
-   nearby/campus learners;
-   course groups;
-   synchronized sessions;
-   group milestones;
-   better chat;
-   contextual discussions.

Goal:

> Test whether social presence improves course completion.

------------------------------------------------------------------------

## Phase 3 --- Knowledge Layer

Build:

-   transcripts;
-   notes;
-   bookmarks;
-   blogs;
-   article discovery;
-   lecture timestamps;
-   course discussions.

Goal:

> Make each course a living knowledge community.

------------------------------------------------------------------------

## Phase 4 --- AI

Build:

-   Ask Lecture;
-   Ask Course;
-   automatic summaries;
-   quizzes;
-   prerequisite detection;
-   personalized revision;
-   AI course organization.

Goal:

> Make the entire course context queryable.

------------------------------------------------------------------------

## Phase 5 --- Network Effects

Build:

-   public profiles;
-   reputation;
-   creator profiles;
-   course recommendations;
-   topic communities;
-   campus communities;
-   high-quality public content discovery.

Goal:

> Make the network itself increasingly useful as it grows.

------------------------------------------------------------------------

# 23. Metrics That Matter

Do NOT optimize primarily for:

-   page views;
-   total watch time;
-   number of messages;
-   raw registrations.

Track:

## Activation

-   \% who start first lecture;
-   time from signup to first lecture;
-   \% who import/join a course.

## Engagement

-   active learning days;
-   lectures completed;
-   weekly learning sessions;
-   study sessions joined.

## Retention

-   D1;
-   D7;
-   D30;
-   weekly active learners.

## Completion

-   lecture completion;
-   module completion;
-   course completion.

## Social effect

Compare:

``` text
Users studying alone
vs
Users with friends/groups
vs
Users using study-together
```

If social users have materially better completion and retention, the
product thesis is validated.

------------------------------------------------------------------------

# 24. The Most Important Experiment

The central hypothesis is:

> **Seeing other people learn increases the probability that a user
> continues learning.**

Test it.

Create cohorts:

### Cohort A

Normal course experience.

### Cohort B

Shows:

> "12 people are studying this course now."

### Cohort C

Shows peers + friends + progress.

### Cohort D

Peers + study together.

Measure:

-   lecture completion;
-   session duration;
-   return rate;
-   course completion.

This is more valuable than blindly adding features.

------------------------------------------------------------------------

# 25. Product Risks

## Risk 1 --- Becomes another distraction platform

Solution:

-   learning-native feed;
-   limited notifications;
-   no addictive short-video feed;
-   social features should return users to learning.

## Risk 2 --- Empty social network

A social product is useless if nobody is online.

Solution:

Start with a concentrated community.

A small active IIT/university community is better than 10,000 inactive
users.

## Risk 3 --- Content rights

Be careful with arbitrary Telegram and YouTube content.

Prefer:

-   user-owned content;
-   authorized content;
-   public/open educational resources;
-   compliant streaming/embedding.

Do not build the business around unauthorized redistribution.

## Risk 4 --- Too many features

The current product can easily become:

``` text
LMS + Reddit + Discord + YouTube + Medium + AI chatbot
```

That would be unfocused.

Every feature should strengthen:

> **Discover → Learn → Socialize around learning → Complete**

If it doesn't strengthen that loop, defer it.

------------------------------------------------------------------------

# 26. Competitive Positioning

Do not try to become another Udemy.

Do not try to become another Coursera.

Do not try to become another Discord.

Do not try to become another Reddit.

Do not try to become another YouTube.

The positioning is:

> **The social layer that helps people actually finish the courses they
> already want to take.**

The unique combination is:

``` text
YouTube-like content availability
+
LMS-like course structure
+
Discord-like peer presence
+
Duolingo-like progress
+
AI contextual assistance
+
Learning-focused social discovery
```

------------------------------------------------------------------------

# 27. Product Principles

These should guide every future development decision.

### Principle 1

**Learning comes before engagement.**

### Principle 2

**Social features should reinforce completion.**

### Principle 3

**Show people learning, not people performing.**

### Principle 4

**Reward progress, not passive consumption.**

### Principle 5

**Make course completion visible.**

### Principle 6

**Keep the learner in context.**

### Principle 7

**Don't build features just because other social networks have them.**

### Principle 8

**Use AI to reduce learning friction, not replace thinking.**

### Principle 9

**Privacy should be default, especially for nearby/campus presence.**

### Principle 10

**Validate behavior before scaling architecture.**

------------------------------------------------------------------------

# 28. Current Product Assessment

Based on the current repository and recent development direction:

### Core idea

**9/10**

Strong behavioral thesis.

### Differentiation

**8.5/10**

The individual components are not novel, but the combination and
positioning are compelling.

### Technical feasibility

**8.5/10**

The current architecture is already capable of supporting a beta.

### Current implementation

**7.5--8/10**

It has moved beyond a toy prototype, but production reliability,
documentation, security, and scaling still need work.

### Retention potential

**9/10**

If peer presence genuinely increases completion, this can be very
sticky.

### Commercial potential

**8/10**

Potential exists, but monetization should not be the immediate focus.

### Overall

**8.7/10**

Worth hosting publicly and testing with real users.

------------------------------------------------------------------------

# 29. Immediate Priority Order

From now on, prioritize roughly in this order:

``` text
1. Reliability
2. Course experience
3. Progress tracking
4. People studying now
5. Friends / groups
6. Study together
7. Trending/discovery
8. Contextual discussion
9. Notes/blogs
10. AI tutor
11. Advanced gamification
12. Creator ecosystem
13. Monetization
```

Do not reverse this order because a feature sounds technically exciting.

------------------------------------------------------------------------

# 30. The Strategic North Star

The ultimate product should feel like:

> You open EduStream because you want to learn something.
>
> You see what other people are learning.
>
> You see that your friend is already 72% through the same course.
>
> You start the lecture.
>
> The player stays with you while you browse the discussion.
>
> Someone asks a question at the exact timestamp you're watching.
>
> You answer it.
>
> You finish the lecture.
>
> Your progress moves.
>
> Your friend finishes another module.
>
> You decide to continue.
>
> Eventually, you finish the course.
>
> Then you write a note or blog that helps the next person.

That is the product.

Not a video host.

Not an LMS.

Not a social network.

**A social operating system for completing courses.**

------------------------------------------------------------------------

# 31. One-Sentence Direction for Future AI/Development Agents

When an AI coding agent is asked to make a product decision, it should
use this as the primary constraint:

> **Build EduStream as a learning-first social operating system whose
> purpose is to help people discover, start, persist with, and complete
> courses through structured content, visible peer activity,
> accountability, collaborative study, knowledge sharing, and contextual
> AI assistance.**

When choosing between two technically viable implementations, prefer the
one that improves:

1.  learning completion;
2.  social accountability;
3.  course discovery;
4.  reliability;
5.  learner context;

in that order.
