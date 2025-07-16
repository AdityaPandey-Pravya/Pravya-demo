import google.generativeai as genai
import os
import json

from dotenv import load_dotenv
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')


PROMPT_TEMPLATE = """
**ROLE:** You are an expert storyteller for the Pravya IPL Challenge.

**CONTEXT & CHARACTERS:**
*   The user is a brilliant Performance Analyst for an IPL team.
*   **Captain Vikram "Vik" Singh:** A cool, strategic veteran. Speaks calmly.
*   **Coach Ravi Sharma:** A young, intense, and stressed-out coach. Speaks with urgency.

**Theme:** The world of IPL cricket - pressure, strategy, and real-time decision-making.

**CRITICAL ROLE: You must TRANSFORM the sample question provided into a new, narrative-driven problem.**
Your primary job is to take the *mathematical concept* and *numbers* from the sample question and completely rewrite the problem so it is born directly from the IPL narrative.

3.  **TRANSFORM, DON'T WRAP:** Do NOT simply repeat the sample question's text. Create a *new* problem description using the same numbers and requiring the same operation, but born from the world.
4.  **Deep Integration:** The problem must feel like an organic challenge that has just emerged within the story, posed by a character like a captain or coach.

---
### **THE GOLDEN RULE OF IMMERSION (NON-NEGOTIABLE)**
The mathematical problem you create MUST be about **on-field cricket strategy, tactics, or real-time player/game statistics.** It must be a question a captain or coach would urgently ask *during the match* to make an immediate decision.

**NEGATIVE CONSTRAINT:** NEVER introduce external scenarios like marketing, ticket sales, merchandise, or player salaries, even if the math fits. The problem must stay within the boundary of the live cricket game.

**GOOD vs. BAD EXAMPLE:**
*   **Sample Math:** 25% of 120.
*   **BAD (Breaks Immersion):** "The marketing team is offering a 25% discount on a ₹120 mini-bat. What's the discount amount?"
*   **GOOD (Maintains Immersion):** "Our bowler has a target of 120 deliveries this match. The coach wants 25% of them to be yorkers. How many yorkers does he need to bowl?"

---
**YOUR TASK: Write the next chapter of the story by following these steps:**

1.  **REACT to the Past:** Based on `[WAS_PREVIOUS_ANSWER_CORRECT]`, start the chapter with a reaction from `[CHARACTER_TO_USE]`. If it was correct, describe the positive on-field result. If false, describe a minor on-field setback.
2.  **ANNOUNCE Achievements:** If `[EARNED_BADGE]` is provided, weave the announcement into the praise (e.g., "That's three correct calls in a row! You've earned the 'Hat-Trick' badge! The dugout is buzzing.").
3.  **CREATE the Next Challenge:** Look at the `[PERFORMANCE_SCORE]` to set the scene.
    *   **Winning Path (Score > 0):** Describe a positive game situation (e.g., "We have them on the ropes," "The run rate is under control").
    *   **High-Pressure Path (Score <= 0):** Describe a tense game situation (e.g., "We just lost a wicket," "The required rate is climbing steeply").
4.  **TRANSFORM the Question (Applying the Golden Rule):** Take the `[SAMPLE_QUESTION_TEXT]` and rewrite it as a natural, urgent problem within the cricket scene you just created.
5.  **PROVIDE a Call to Action:** End with a clear, short instruction.

**OUTPUT FORMAT:** Respond with ONLY a valid JSON object with two keys: `"narrative_chapter"` and `"call_to_action"`.

---
**BEGINNING OF TASK**

*   **Game State:**
    *   `[MASTERY]:` {mastery}
    *   `[PERFORMANCE_SCORE]:` {performance_score}
    *   `[CHARACTER_TO_USE]:` {character_to_use}
*   **Previous Turn's Result:**
    *   `[WAS_PREVIOUS_ANSWER_CORRECT]:` {was_correct}
    *   `[EARNED_BADGE]:` {earned_badge}
*   **New Problem to Integrate:**
    *   `[SAMPLE_QUESTION_CONCEPT]:` {title}
    *   `[SAMPLE_QUESTION_TEXT]:` {question_text}
"""

HINT_PROMPT_TEMPLATE = """
**Role:** You are a helpful teammate in the IPL dugout.
**Character:** Speak as {character}.
**Task:** The user is stuck on this problem: "{question_text}". Give them a story-based hint that does NOT contain numbers or mathematical terms. Frame it as a piece of cricket strategy to guide their thinking.
"""

# === THIS IS THE CORRECTED SECTION ===
def generate_story_for_question(question: dict, mastery: str, performance_score: int, was_correct: bool | None, earned_badge: str | None) -> dict:
    # Determine which character should be speaking based on pressure
    character = "Captain Vik" if performance_score > 0 else "Coach Ravi"

    try:
        prompt = PROMPT_TEMPLATE.format(
            mastery=mastery,
            performance_score=performance_score,
            character_to_use=character,
            was_correct=was_correct,
            earned_badge=earned_badge,
            title=question.get('title'),
            question_text=question.get('question_text')
        )
        response = model.generate_content(prompt)
        
        print("--- LLM Raw Response ---")
        print(response.text)
        print("------------------------")
        
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        story_data = json.loads(cleaned_response_text)
        story_data['question_details'] = question # Pass along for the hint system
        return story_data

    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! CRITICAL ERROR in story_generator: {e} !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return {
            "narrative_chapter": f"An error occurred. Raw Challenge: {question.get('question_text')}",
            "call_to_action": "Solve the problem above.",
            "question_details": question
        }

def generate_narrative_hint(question_text: str, character: str) -> str:
    try:
        prompt = HINT_PROMPT_TEMPLATE.format(question_text=question_text, character=character)
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Sorry, the dugout is too loud right now. Try to think about the core of the problem."