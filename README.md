# VGC Mega-Meta Architect

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B)
![Pandas](https://img.shields.io/badge/Data-Pandas-150458)
![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E)

## 📌 Project Overview
The **VGC Mega-Meta Architect** is a comprehensive, data-driven analytical tool and battle simulation engine designed for Pokémon Video Game Championships (VGC). 

Rather than relying on human intuition, this engine scrapes raw mechanical data directly from the official Pokémon Showdown repositories, processes it through machine learning pipelines (clustering, synergy scoring), and feeds it into a custom-built, fully automated 4v4 battle simulator. The project aims to evaluate team viability, predict matchup momentums against the meta, and simulate games to optimize team cores before touching a Nintendo Switch.

---

## 🏗️ Architecture & Features

### 1. Automated Data Pipeline (`src/showdown_parser.py`)
*   **Live Data:** Directly pulls compiled JavaScript endpoints (`moves.js`, `items.ts`, `abilities.js`) from Pokémon Showdown and parses them into structured CSVs.
*   **Mechanical Flags:** Automatically extracts mechanical DNA such as `selfSwitch` (Pivots), `recoil`, `drain`, priority brackets, and secondary effects, meaning moves don't have to be hardcoded.

### 2. Machine Learning Analysis (`src/synergy_scorer.py`, `src/counter_recommender.py`)
*   **Role Clustering:** Categorizes Pokémon into offensive, defensive, and support roles based on BST and usage.
*   **Synergy Scorer:** Analyzes 4-Pokémon cores for defensive overlaps, resistance coverage, and speed tier variance.
*   **Threat Matchup:** Predicts win probabilities against top meta threats (e.g., Flutter Mane, Urshifu) using aggregated stats.

### 3. Full VGC Battle Engine (`src/battle_engine.py`)
A custom Python simulation engine that handles complex VGC mechanics:
*   **Dynamic Speed & Priority:** Resolves turn order dynamically, accounting for Trick Room, Tailwind, Priority brackets (Fake Out, Prankster), and dynamic speed changes.
*   **Redirection & Status:** Fully implements Rage Powder, Follow Me, Encore, Sleep, Freeze, Paralysis, Burn, and Poison.
*   **Pivoting & Items:** Automates self-switching moves (Parting Shot, U-turn), Life Orb recoil, Rocky Helmet chip, Choice item move locks, and Berry consumption mid-turn.
*   **AI Agent:** A `SmartVGCAgent` that makes heuristic-based decisions, understanding when it is Choice-locked or Encored.

### 4. Interactive Dashboard (`app/streamlit_app.py`)
*   **Team Builder:** Select a 4-Pokémon core and receive real-time synergy scores and counter recommendations.
*   **Battle Simulator:** A "Bring 4, Pick 4" UI where users can equip items, customize movesets (with intelligent STAB suggestions), and watch the AI engine play out a full log-detailed battle.

---

## ✅ Progress So Far (What Works)
- [x] **Data Ingestion:** Successfully extracting Moves, Base Stats, Items, and Type Charts.
- [x] **UI:** Streamlit dashboard is fully functional with both ML Analysis and Battle Simulation tabs.
- [x] **Battle Logistics:** 4v4 team formatting, bench swapping, and fainting logic.
- [x] **Core Mechanics:** STAB, physical/special splits, type effectiveness, and spread move damage modifiers (0.75x).
- [x] **Advanced Mechanics:** Complex volatile statuses (Encore/Rage Powder), end-of-turn damage (Burn/Poison), and data-driven flags (Recoil/Drain/Pivots).

---

## 🚧 Current Limitations (What's Lacking)
While the engine is robust, a few deep mechanics are currently simplified or missing:
*   **Abilities:** Only Entry abilities (Weather/Terrain setters, Intimidate) and Priority blockers (Armor Tail) are implemented. Mid-turn passive abilities (e.g., *Huge Power*, *Levitate*, *Defiant*) are not yet automated.
*   **Complex Targeting:** The AI agent currently chooses targets heuristically; it doesn't calculate exact optimal damage paths for spread vs. single-target.
*   **Stat Stages Check:** The engine allows stat changes, but does not cap them strictly at +6/-6 internally yet.
*   **Protect Scaling:** Protect currently works, but the 1/3 success rate penalty for consecutive uses is not enforced.

---

## 🚀 Future Implementations
1.  **Terastalization System:** Add UI toggles for Tera Types, dynamically altering STAB and defensive profiles mid-simulation.
2.  **Passive Ability Automation:** Update `get_stat` and the damage formula to parse ability flags from the Showdown data.
3.  **Monte Carlo Tree Search (MCTS) AI:** Replace the current heuristic `SmartVGCAgent` with a neural-net or MCTS-driven agent capable of evaluating multiple turn depths to find optimal plays.
4.  **Live Usage Stats Integration:** Pull real-time Pikalytics/Showdown ladder data to automatically assign the most meta-accurate EV spreads and natures to the simulation.
