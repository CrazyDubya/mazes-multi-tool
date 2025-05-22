# llm_interface.py

class LLMInterface:
    def generate_checklist(self, prompt):
        # Simulated LLM interaction based on keywords
        prompt = prompt.lower()
        if 'web' in prompt:
            simulated_checklist = {
                'tasks': [
                    {'task': 'Set up web server', 'completed': False},
                    {'task': 'Design homepage', 'completed': False},
                    {'task': 'Implement API endpoints', 'completed': False}
                ]
            }
        elif 'data' in prompt:
            simulated_checklist = {
                'tasks': [
                    {'task': 'Collect data samples', 'completed': False},
                    {'task': 'Clean and preprocess data', 'completed': False},
                    {'task': 'Train machine learning model', 'completed': False}
                ]
            }
        else:
            simulated_checklist = {
                'tasks': [
                    {'task': 'Initialize project repository', 'completed': False},
                    {'task': 'Write project documentation', 'completed': False},
                    {'task': 'Set up CI/CD pipeline', 'completed': False}
                ]
            }
        return simulated_checklist