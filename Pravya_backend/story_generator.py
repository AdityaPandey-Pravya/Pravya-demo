import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

PROMPT_TEMPLATE = """
**Role:** You are a master storyteller and Narrative Problem Designer for the high-stakes Indian Premier League (IPL).

**Theme:** The world of IPL cricket - pressure, strategy, and real-time decision-making.

**CRITICAL ROLE: You must TRANSFORM the sample question provided into a new, narrative-driven problem.**
Your primary job is to take the *mathematical concept* and *numbers* from the sample question and completely rewrite the problem so it is born directly from the IPL narrative.

**Core Rules:**
1.  **Narrate the Outcome (CRUCIAL):**
    *   If [WAS_PREVIOUS_ANSWER_CORRECT] is **True**: Start the story with positive reinforcement. Acknowledge the Analyst's correct calculation and describe its positive impact on the game (e.g., "Your perfect analysis gave the captain the confidence to make a bold move...").
    *   If [WAS_PREVIOUS_ANSWER_CORRECT] is **False**: Start with a narrative of a minor setback. The team had to adapt because the calculation wasn't quite right. Keep it encouraging, not punishing (e.g., "Close, but the numbers were slightly off. The team had to pivot their strategy on the fly...").
    *   If [WAS_PREVIOUS_ANSWER_CORRECT] is null (the first question), just start the story directly.
2.  **Announce Power-ups:** If [EARNED_POWER_UP] is not null, weave it into the positive narration. Example: "Your pinpoint accuracy has boosted team morale, earning you the **'Captain's Confidence'** power-up! You feel a new level of trust from the dugout."
3.  **TRANSFORM, DON'T WRAP:** Do NOT simply repeat the sample question's text. Create a *new* problem description using the same numbers and requiring the same operation, but born from the world.
4.  **Deep Integration:** The problem must feel like an organic challenge that has just emerged within the story, posed by a character like a captain or coach.

**Inputs You Will Receive:**
*   **[MASTERY]:** The user's area of expertise.
*   **[SAMPLE_QUESTION_CONCEPT]:** The title/concept of the sample question.
*   **[SAMPLE_QUESTION_TEXT]:** The raw sample question to take inspiration from.
*   **[PREVIOUS_STORY_CONTEXT]:** The last story chapter the user saw.
*   **[POWER_UPS]:** A list of special abilities the user has earned.
*   **[WAS_PREVIOUS_ANSWER_CORRECT]:** True, False, or null.
*   **[EARNED_POWER_UP]:** The name of a new power-up, or null.

**Output Format:** Respond with a single, valid JSON object, with no other text before or after it:
*   `"narrative_chapter"`: Your story, which starts with feedback and then introduces the new, fully integrated problem.
*   `"call_to_action"`: A short, direct instruction (e.g., "Calculate the required run rate and enter it below!").

---
**BEGINNING OF TASK**

*   **[MASTERY]:** {mastery}
*   **[SAMPLE_QUESTION_CONCEPT]:** {title}
*   **[SAMPLE_QUESTION_TEXT]:** {question_text}
*   **[PREVIOUS_STORY_CONTEXT]:** {previous_context}
*   **[POWER_UPS]:** {power_ups}
*   **[WAS_PREVIOUS_ANSWER_CORRECT]:** {was_correct}
*   **[EARNED_POWER_UP]:** {earned_power_up}
"""

def generate_story_for_question(mastery: str, question: dict, previous_context: str, power_ups: list, was_correct: bool | None, earned_power_up: str | None) -> dict:
    """Calls the Generative AI model to create a story chapter."""
    try:
        prompt = PROMPT_TEMPLATE.format(
            mastery=mastery,
            title=question.get('title'),
            question_text=question.get('question_text'),
            previous_context=previous_context or "It's the strategic timeout in a high-stakes qualifier match. The game is on a knife's edge.",
            power_ups=power_ups or "None yet.",
            was_correct=was_correct,
            earned_power_up=earned_power_up
        )

        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        story_data = json.loads(cleaned_response_text)
        
        return story_data

    except Exception as e:
        print(f"Error during story generation: {e}")
        fallback_narrative = "An unexpected error occurred during narrative generation. The raw challenge is below."
        if was_correct:
            fallback_narrative = "Correct! But an error occurred. Here is the next challenge."
        elif was_correct is False:
             fallback_narrative = "That wasn't quite right. An error occurred. Here is the next challenge."

        return {
            "narrative_chapter": f"{fallback_narrative}\n\n**{question.get('title')}**\n{question.get('question_text')}",
            "call_to_action": "Please solve the problem above.",
        }