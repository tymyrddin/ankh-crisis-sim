# Ankh-Morpork critical infrastructure simulation (Sketches)

This project is a Python-based simulation game that models how disruptions in digital and operational systems 
translate into real-world consequences for cities, organisations, and the people who depend on them.

Set in the fictional city of Ankh-Morpork, the simulation uses a familiar urban environment to explore modern 
challenges around critical infrastructure, governance, and resilience — without relying on technical detail or 
domain-specific jargon.

The setting is fictional. The dynamics are not.

## Purpose

The simulation is designed to support conversations and workshops around:

* The impact of digital and operational disruptions on:

  * public services
  * economic activity
  * trust and legitimacy
  * regulatory and political pressure
* Decision-making under uncertainty, time pressure, and budget constraints
* The cascading effects of infrastructure failures across sectors
* The relationship between operational choices and societal outcomes

Rather than focusing on how systems are built, the simulation focuses on what happens when they fail, degrade, or are disrupted.

## Audience

This project is intended for use with:

* Executive leadership
* Board members
* Policy makers
* Regulators
* Public-sector decision-makers
* Mixed technical / non-technical groups in joint exercises

No prior technical or cybersecurity knowledge is required to participate.

## What the simulation does

Players take responsibility for a city with interconnected services, including:

* Energy
* Water and sanitation
* Communications
* Transport
* Public and private facilities
* Residential areas

Each building or district represents a concentration of services and dependencies rather than a single system.

Over time, the city experiences incidents, disruptions, and stressors inspired by real-world OT, ICS, and digital infrastructure risks. These events affect:

* service availability
* economic output
* public sentiment
* institutional trust
* regulatory scrutiny

Players respond by allocating resources, prioritising interventions, and managing trade-offs between short-term stability and long-term resilience.

## What the simulation is not

* It is not a technical training tool
* It does not simulate networks, protocols, or exploits
* It does not reward detailed technical knowledge
* It is not a competitive or leaderboard-based game

The emphasis is on outcomes, consequences, and choices, not on technical mechanisms.

## Why Ankh-Morpork?

Using a fictional city allows participants to:

* Engage seriously without referencing real-world sensitive locations
* Speak openly about failure, pressure, and trade-offs
* Recognise familiar patterns without defensive reactions

The city’s exaggerated complexity and personality make interdependencies visible and memorable, while keeping discussions grounded in reality.

## Technology

* Language: Python 3.12
* Framework: Arcade (2D game and UI)
* Architecture: modular, scenario-driven simulation
* Designed for facilitated sessions and workshops

## Status

This project is under active development.
The current focus is on building a robust infrastructure threat and impact model, which will serve as the foundation for scenarios and gameplay.

## License and usage

This project is licensed under the [Polyform Noncommercial Licence](LICENSE).

You are welcome to use this software for:

- Learning and experimentation
- Academic or independent research
- Defensive security research
- Developing and validating proof-of-concepts
- Incident response exercises
- Non-commercial red/blue team simulations

You may not use this software for:

- Paid workshops or training
- Consultancy or advisory services
- Internal corporate training
- Commercial product development

If you want to use this project in a paid or commercial context, a commercial licence is required.  
See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) for details.

This project is actively developed and maintained to support realistic security research and training.  
The licence ensures that:

- Security research remains accessible
- Defensive knowledge can spread
- Commercial exploitation is fair and sustainable

If you are unsure whether your use case is commercial, ask. [Ambiguity is solvable](https://tymyrddin.dev/contact/); silence is not.

