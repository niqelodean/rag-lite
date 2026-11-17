import json
import sys
import os

# Add the parent directory to sys.path so we can import retrieve.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieve import Retriever

def run_evaluation():
    # 1. Load the ground truth dataset
    with open("eval/questions.json", "r") as f:
        test_cases = json.load(f)

    # 2. Initialize the retriever (this loads chunks.json and builds BM25)
    print("Loading retriever...")
    retriever = Retriever()

    # Variables to track scores
    total_questions = len(test_cases)
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    mrr_sum = 0.0

    print(f"\nRunning evaluation on {total_questions} questions...\n")

    # 3. Loop through each question
    for case in test_cases:
        question = case["question"]
        expected_file = case["expected_file"]
        
        # We search for top 5 chunks
        results = retriever.search(question, k=5)
        
        # Extract just the source file names from the results
        retrieved_files = [r["source"] for r in results]
        
        # Find where the expected file appears in the results (0 if not found)
        rank = None
        for i, file in enumerate(retrieved_files):
            if file == expected_file:
                rank = i + 1 # Rank is 1-indexed (1st place, 2nd place, etc.)
                break

        # Update metrics
        if rank is not None:
            if rank == 1: hits_at_1 += 1
            if rank <= 3: hits_at_3 += 1
            if rank <= 5: hits_at_5 += 1
            
            mrr_sum += 1.0 / rank
            
            print(f" [{rank}] {question[:50]:<50} -> found {expected_file}")
        else:
            print(f" {question[:50]:<50} -> MISSED (Expected {expected_file})")
            print(f"       Got: {retrieved_files[0]}")

    # 4. Calculate final metrics
    hit_rate_1 = (hits_at_1 / total_questions) * 100
    hit_rate_3 = (hits_at_3 / total_questions) * 100
    hit_rate_5 = (hits_at_5 / total_questions) * 100
    mrr = mrr_sum / total_questions

    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"Hit Rate @ 1: {hit_rate_1:.1f}%  (Correct file was the #1 result)")
    print(f"Hit Rate @ 3: {hit_rate_3:.1f}%  (Correct file was in top 3)")
    print(f"Hit Rate @ 5: {hit_rate_5:.1f}%  (Correct file was in top 5)")
    print(f"MRR:          {mrr:.3f}     (Mean Reciprocal Rank - closer to 1.0 is better)")
    print("="*60)

if __name__ == "__main__":
    run_evaluation()