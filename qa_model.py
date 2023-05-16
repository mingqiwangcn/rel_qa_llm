from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline

class QAModel: 
    def __init__(self):
        model_name = "deepset/roberta-base-squad2"
        self.nlp = pipeline('question-answering', model=model_name, tokenizer=model_name, top_k=20)
    
    def __call__(self, question, passage):
        input_text = {
            'question':question,
            'context':passage,
        }
        res = self.nlp(input_text)
        return res


