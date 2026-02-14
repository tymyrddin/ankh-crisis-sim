# Ankh-Morpork Critical Infrastructure Threat Model

The tabularised short version. For the verbose version, see [Critical infrastructure in Ankh-Morpork](https://purple.tymyrddin.dev/docs/lantern/dilemma/threat-modelling/).

| Domain                  | Trigger / Threat                               | Disruption                                        | Immediate Impact                                           | Secondary Impact                                                   | Dependencies                                                               | Decision Pressure                                                                             | Recovery Options                                                                            |
|-------------------------|------------------------------------------------|---------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Energy Supply           | Rolling outage, degraded generation            | Unstable power, blackouts                         | Households lose heating/power; businesses suspend ops      | Economic loss; media attention; public frustration                 | Communications, Water, Transport, Public services, Commercial, Residential | Prioritise allocation; justify unequal supply; balance emergency spend vs long-term stability | Technical restoration; Resilience investment; Compensatory measures; Accountability actions |
| Water & Sanitation      | Pump failure; contamination; supply disruption | Unsafe water; reduced pressure; wastewater backup | Households affected; hospitals at risk                     | Public alarm; health authority involvement; trust erosion          | Energy, Communications, Public services, Residential                       | Act fast at any cost; communicate clearly; accept visible disruption                          | Technical restoration; Resilience investment; Compensatory measures; Accountability actions |
| Communications          | Clacks tower failure; network outage           | Loss of internet/clacks; degraded coordination    | Services struggle to coordinate; citizens lose information | Rumours spread; leadership appears absent                          | Energy, Public services, Commercial, Residential                           | Restore communication first; manage narrative; prioritise high-impact nodes                   | Technical restoration; Resilience investment                                                |
| Transport & Movement    | Bridge collapse; traffic control failure       | Bridge closures; tram/omnibus stoppage            | Daily disruption; workforce mobility affected              | Economic slowdown; public irritation                               | Energy, Communications, Commercial, Public services                        | Accept risk or prolong outage; prioritise commerce vs safety                                  | Technical restoration; Resilience investment                                                |
| Public Services         | Hospital system outage; Watch delayed          | Emergency response delays; care disruption        | Direct risk to life; critical service failure              | Regulatory scrutiny; political accountability; reputational damage | Energy, Communications, Transport, Water                                   | Allocate scarce resources; spare no expense; manage optics                                    | Technical restoration; Resilience investment; Compensatory measures; Accountability actions |
| Commercial & Industrial | Payment system failure; supply chain break     | Production downtime; logistics stalled            | Financial losses; workforce disruption                     | Lobbying; media framing; economic instability                      | Energy, Communications, Transport, Water                                   | Decide which sectors to protect; justify public support                                       | Technical restoration; Resilience investment; Compensatory measures                         |
| Residential Areas       | Combined utility outages                       | Power/water/communications loss                   | Daily life affected; emotional response                    | Protests; political legitimacy loss; crisis fatigue                | All above                                                                  | Restore dignity; manage equity; prioritise high-impact areas                                  | Technical restoration; Resilience investment; Compensatory measures                         |

## Notes on triggers

* Degradation & neglect: ageing pumps, unattended clacks towers, overused bridges
* Operational error: misconfigured flow, human error during upgrades
* Supply chain & vendor failure: single clacks company, single engineering guild
* Criminal interference: ransomware, extortion of commercial services
* Ideological disruption: guild protest shutting down markets, sabotage of bridges
* Strategic/state-aligned interference: ambiguous repeated small outages, testing response

## Recovery pathways

| Option                 | Description                        | Pros                                     | Cons                                            |
|------------------------|------------------------------------|------------------------------------------|-------------------------------------------------|
| Technical restoration  | Fix the immediate failure          | Fast                                     | May not prevent recurrence; expensive in crisis |
| Resilience investment  | Upgrade systems, add redundancy    | Reduces future risk; visible improvement | Slow, politically hard to justify; costly       |
| Compensatory measures  | Financial/operational compensation | Quick appeasement; restores goodwill     | Does not fix system; may create moral hazard    |
| Accountability actions | Investigations, firings, contracts | Restores trust in governance             | Divisive; may slow recovery                     |

## Amplifiers / systemic stressors

* Austerity / underinvestment: magnifies degradation, misconfigurations
* Just-in-time logistics: amplifies transport & commercial disruption
* Vendor monoculture: single points of failure create outsized impact
* Social/spatial inequality: unequal restoration → trust erosion
* Organisational fragmentation: slows response, amplifies error
* Narrative effects: visibility, symbolism, and duration shape political pressure
