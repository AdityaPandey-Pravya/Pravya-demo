from google import genai

client = genai.Client(api_key="AIzaSyA9kbG9EF41WLq9Kc5h669ZCKRFo3L4NEw")
prompt = "The quick brown fox jumps over the lazy dog."

# # Count tokens using the new client method.
# total_tokens = client.models.count_tokens(
#     model="gemini-2.0-flash", contents=prompt
# )
# print("total_tokens: ", total_tokens)
# # ( e.g., total_tokens: 10 )

response = client.models.generate_content(
    model="gemini-2.5-flash", contents=prompt
)

# The usage_metadata provides detailed token counts.
print(f"{response.text},{response.usage_metadata.prompt_token_count}, {response.usage_metadata.candidates_token_count},{response.usage_metadata.total_token_count}" )
# ( e.g., prompt_token_count: 11, candidates_token_count: 73, total_token_count: 84 )