import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
load_dotenv()

# Configure the generative AI client with the API key from the environment
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Create a Gemini Pro model instance
model = genai.GenerativeModel('gemini-2.5-flash')

# This is the heart of our storytelling.
# It's a highly-detailed prompt designed to force the LLM
# to intertwine the question with the IPL narrative.


PROMPT_TEMPLATE = """
**Role:** You are a master storyteller and Narrative Problem Designer for the high-stakes Indian Premier League (IPL).

**Theme:** The world of IPL cricket - pressure, strategy, and real-time decision-making.

**CRITICAL NEW ROLE: You must TRANSFORM the sample question provided into a new, narrative-driven problem.**
Your primary job is to take the *mathematical concept* and *numbers* from the sample question and completely re-imagine and rewrite the problem so it is born directly from the IPL narrative.

**Core Rules:**
1.  **Deep Integration:** The problem must feel like an organic challenge that has just emerged within the story. It should be posed by a character like a captain or coach.
2.  **TRANSFORM, DON'T WRAP:** Do NOT simply tell a story and then repeat the sample question's text. You must create a *new* problem description that uses the same numbers and requires the same mathematical operation.
3.  **Example of Transformation:**
    *   If the sample question is: "What is 75% of 160?"
    *   Your narrative should create a problem like: "The opposition set a target of 160. Our data analyst says our win probability jumps if our star batsman scores 75% of those runs himself. How many runs does he need to score?"
    *   The numbers (75, 160) are the same, the operation (percentage) is the same, but the problem is now entirely part of the world.

**Inputs You Will Receive:**
*   **[MASTERY]:** The user's area of expertise.
*   **[SAMPLE_QUESTION_CONCEPT]:** The title/concept of the sample question.
*   **[SAMPLE_QUESTION_TEXT]:** The raw sample question to take inspiration from.
*   **[PREVIOUS_STORY_CONTEXT]:** The last story chapter the user saw.
*   **[POWER_UPS]:** A list of special abilities the user has earned.

**Instructions:**
1.  **Continue the Narrative:** Seamlessly continue the story from the [PREVIOUS_STORY_CONTEXT].
2.  **Introduce the Conflict:** Create a new, urgent situation in the story (e.g., a strategic timeout, a sudden collapse, a rain-affected target).
3.  **Embed the Transformed Problem:** Have a character pose the newly-scripted problem to the user (the Analyst).
4.  **Maintain Tone:** Keep it dramatic, urgent, and exciting. Use cricket terminology.
5.  **Output Format:** Respond with a single, valid JSON object, with no other text before or after it:
    *   `"narrative_chapter"`: Your story, which now contains the fully integrated problem.
    *   `"call_to_action"`: A short, direct instruction (e.g., "Calculate the required run rate and enter it below!").

---
**BEGINNING OF TASK**

*   **[MASTERY]:** {mastery}
*   **[SAMPLE_QUESTION_CONCEPT]:** {title}
*   **[SAMPLE_QUESTION_TEXT]:** {question_text}
*   **[PREVIOUS_STORY_CONTEXT]:** {previous_context}
*   **[POWER_UPS]:** {power_ups}
"""

# Rename variables in the `generate_story_for_question` function to match the prompt
def generate_story_for_question(mastery: str, question: dict, previous_context: str, power_ups: list) -> dict:
    try:
        # Format the master prompt with the specific details
        prompt = PROMPT_TEMPLATE.format(
            mastery=mastery,
            title=question.get('title'), # Now used as 'SAMPLE_QUESTION_CONCEPT'
            question_text=question.get('question_text'), # Now used as 'SAMPLE_QUESTION_TEXT'
            previous_context=previous_context or "It's the strategic timeout in a high-stakes qualifier match. The game is on a knife's edge.",
            power_ups=power_ups or "None yet."
        )

        # Call the LLM
        response = model.generate_content(prompt)
        
        # Clean up the response to ensure it's valid JSON
        # The API can sometimes wrap the JSON in ```json ... ```
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        # Parse the JSON response from the LLM
        story_data = json.loads(cleaned_response_text)
        
        return {
            "narrative_chapter": story_data.get("narrative_chapter"),
            "call_to_action": story_data.get("call_to_action"),
            "question_details": question # Pass along the original question data
        }

    except Exception as e:
        print(f"Error during story generation: {e}")
        # Provide a fallback in case the LLM fails
        return {
            "narrative_chapter": "An unexpected error occurred. The system is rebooting. Here is the raw challenge:",
            "call_to_action": "Please solve the following:",
            "question_details": question
        }