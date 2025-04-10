from collections import defaultdict

import numpy as np
from report.report_utils import render_template
import matplotlib.pyplot as plt
import base64
import io


def questionnaire_report(
    questionnaire,
    questionnaire_response,
    include_bar_chart=False,
    include_pie_chart=False,
    include_line_chart=False,
):
    """
    Generates a report for a given questionnaire and its corresponding response.

    Args:
        questionnaire (dict): The questionnaire data.
        questionnaire_response (dict): The questionnaire response data.
        include_bar_chart (bool): Whether to include a bar chart in the report.
        include_pie_chart (bool): Whether to include a pie chart in the report.
        include_line_chart (bool): Whether to include a line chart in the report.

    Returns:
        str: The generated report as HTML.
    """
    report_title = questionnaire.get("title", "N/A")

    # Map the questions and answers
    questions = {item["linkId"]: item for item in questionnaire.get("item", [])}
    responses = {
        item["linkId"]: item for item in questionnaire_response.get("item", [])
    }

    total_score = 0
    question_scores = []  # List to store scores for plotting
    question_texts = []  # List to store question texts for plotting

    # Process the questions and answers
    question_data = []
    for link_id, question in questions.items():
        question_text = question.get("text", "N/A")
        question_type = question.get("type", "N/A")

        if question_type == "display":
            # Handle display type as informational text
            question_data.append({"question": question_text, "answer": "INFO"})
        else:
            # Handle regular questions with answers
            response_item = responses.get(link_id, {})
            answer = response_item.get("answer", [{}])[0]

            # Check for different answer types
            answer_display = answer.get("valueCoding", {}).get("display")
            answer_integer = answer.get("valueInteger")
            answer_string = answer.get("valueString")

            # Determine the answer to display
            if answer_display:
                answer_text = answer_display
            elif answer_integer is not None:
                answer_text = str(answer_integer)
            elif answer_string:
                answer_text = answer_string
            else:
                answer_text = "No answer provided"

            # Extract ordinal value if available
            ordinal_value = None
            for option in question.get("answerOption", []):
                if option.get("valueCoding", {}).get("display") == answer_display:
                    ordinal_value = option.get("extension", [{}])[0].get("valueDecimal")
                    break

            # Add ordinal value to the total score if applicable
            if ordinal_value is not None:
                total_score += ordinal_value
                question_scores.append(ordinal_value)
            elif answer_integer is not None:
                # If the answer is a plain integer, add it to the total score
                total_score += answer_integer
                question_scores.append(answer_integer)
            else:
                question_scores.append(
                    0
                )  # Default score for unanswered or non-scored questions

            question_texts.append(question_text)
            question_data.append({"question": question_text, "answer": answer_text})

    # Generate plots for the scores
    chart_images = []
    if question_scores:
        if include_bar_chart:
            bar_chart_base64 = generate_bar_chart_base64(
                question_texts, question_scores, report_title
            )
            chart_images.append(bar_chart_base64)

        if include_pie_chart:
            pie_chart_base64 = generate_pie_chart_base64(
                question_texts, question_scores, report_title
            )
            chart_images.append(pie_chart_base64)

        if include_line_chart:
            line_chart_base64 = generate_line_chart_base64(
                question_texts, question_scores, report_title
            )
            chart_images.append(line_chart_base64)

    # Render the report using a template
    context = {
        "title": report_title,
        "questions": question_data,
        "total_score": total_score,
        "charts": chart_images,
    }
    html = render_template("template_questionnaire.html", context)
    return html


def questionnaire_progress_report(
    questionnaire,
    questionnaire_responses,
    include_bar_chart=False,
    include_line_chart=False,
):
    """
    Generates a report for a given questionnaire and its corresponding responses.

    Args:
        questionnaire (dict): The questionnaire data.
        questionnaire_responses (list[dict]): A list of questionnaire response data.
        include_bar_chart (bool): Whether to include a bar chart for progress.
        include_line_chart (bool): Whether to include a line chart for progress.

    Returns:
        str: The generated report as HTML.
    """
    report_title = questionnaire.get("title", "N/A")

    # Map the questions
    questions = {item["linkId"]: item for item in questionnaire.get("item", [])}

    # Prepare data for comparison
    progress_data = defaultdict(lambda: {"dates": [], "scores": [], "answers": []})
    total_scores = []

    for response in questionnaire_responses:
        response_date = response.get("authored", "Unknown Date")
        responses = {item["linkId"]: item for item in response.get("item", [])}

        total_score = 0
        for link_id, question in questions.items():
            question_text = question.get("text", "N/A")
            question_type = question.get("type", "N/A")

            if question_type != "display":
                response_item = responses.get(link_id, {})
                answer = response_item.get("answer", [{}])[0]

                # Check for different answer types
                answer_display = answer.get("valueCoding", {}).get("display")
                answer_integer = answer.get("valueInteger")
                answer_string = answer.get("valueString")

                # Determine the answer to display
                if answer_display:
                    answer_text = answer_display
                elif answer_integer is not None:
                    answer_text = str(answer_integer)
                elif answer_string:
                    answer_text = answer_string
                else:
                    answer_text = "No answer provided"

                # Extract ordinal value if available
                ordinal_value = None
                for option in question.get("answerOption", []):
                    if option.get("valueCoding", {}).get("display") == answer_display:
                        ordinal_value = option.get("extension", [{}])[0].get(
                            "valueDecimal"
                        )
                        break

                # Add ordinal value to the total score if applicable
                if ordinal_value is not None:
                    total_score += ordinal_value
                elif answer_integer is not None:
                    total_score += answer_integer

                # Store progress data
                progress_data[question_text]["dates"].append(response_date)
                progress_data[question_text]["scores"].append(
                    ordinal_value if ordinal_value is not None else answer_integer or 0
                )
                progress_data[question_text]["answers"].append(answer_text)

        total_scores.append({"date": response_date, "score": total_score})

    # Generate charts for progress
    chart_images = []
    if include_line_chart:  # Now generates a line chart for total scores
        line_chart_base64 = generate_total_scores_line_chart(total_scores, report_title)
        chart_images.append(line_chart_base64)

    if include_bar_chart:  # Now generates bar charts for question responses
        bar_chart_base64 = generate_questions_bar_chart(progress_data, report_title)
        chart_images.append(bar_chart_base64)

    line_chart_base64 = generate_questions_line_chart(progress_data, report_title)
    chart_images.append(line_chart_base64)

    # Render the report using a template
    context = {
        "title": report_title,
        "progress_data": progress_data,
        "total_scores": total_scores,
        "charts": chart_images,
    }
    html = render_template("template_questionnaire_progress.html", context)
    return html


def generate_bar_chart_base64(question_texts, question_scores, report_title):
    """
    Generates a bar chart for the questionnaire scores and returns it as a Base64 string.

    Returns:
        str: The Base64-encoded image.
    """
    plt.figure(figsize=(10, 6))
    plt.barh(question_texts, question_scores, color="skyblue")
    plt.xlabel("Scores")
    plt.ylabel("Questions")
    plt.title(f"Scores for {report_title}")
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def generate_pie_chart_base64(question_texts, question_scores, report_title):
    """
    Generates a pie chart for the questionnaire scores and returns it as a Base64 string.

    Returns:
        str: The Base64-encoded image.
    """
    plt.figure(figsize=(8, 8))
    plt.pie(
        question_scores,
        labels=question_texts,
        autopct="%1.1f%%",
        startangle=140,
        colors=plt.cm.Paired.colors,
    )
    plt.title(f"Score Distribution for {report_title}")
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def generate_line_chart_base64(question_texts, question_scores, report_title):
    """
    Generates a line chart for the questionnaire scores and returns it as a Base64 string.

    Returns:
        str: The Base64-encoded image.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(question_texts, question_scores, marker="o", linestyle="-", color="green")
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Questions")
    plt.ylabel("Scores")
    plt.title(f"Scores Trend for {report_title}")
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def generate_total_scores_line_chart(total_scores, report_title):
    """
    Generates a line chart for total scores over time and returns it as a Base64 string.

    Args:
        total_scores (list): List of dictionaries containing date and score
        report_title (str): Title of the report

    Returns:
        str: The Base64-encoded image.
    """
    dates = [entry["date"] for entry in total_scores]
    scores = [entry["score"] for entry in total_scores]

    plt.figure(figsize=(10, 6))
    plt.plot(dates, scores, marker="o", linestyle="-", color="green")
    plt.xlabel("Dates")
    plt.ylabel("Total Scores")
    plt.title(f"Total Scores Over Time for {report_title}")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def generate_questions_bar_chart(progress_data, report_title):
    """
    Generates grouped bar charts for question responses over time.

    Args:
        progress_data (dict): Dictionary containing question progress data
        report_title (str): Title of the report

    Returns:
        str: The Base64-encoded image.
    """
    plt.figure(figsize=(12, 8))

    # For simplicity, we'll take the first few questions if there are many
    questions = list(progress_data.keys())
    if len(questions) > 5:
        questions = questions[:5]  # Limit to first 5 questions for readability

    x = np.arange(len(questions))
    width = 0.8 / len(progress_data[questions[0]]["dates"])

    # Get unique dates across all questions
    all_dates = []
    for question in questions:
        all_dates.extend(progress_data[question]["dates"])
    unique_dates = sorted(set(all_dates))

    # Create bar groups for each date
    for i, date in enumerate(unique_dates[:5]):  # Limit to first 5 dates if many
        scores_for_date = []
        for question in questions:
            # Find the score for this date if it exists
            date_idx = None
            try:
                date_idx = progress_data[question]["dates"].index(date)
                scores_for_date.append(progress_data[question]["scores"][date_idx])
            except ValueError:
                scores_for_date.append(0)  # No data for this question on this date

        plt.bar(x + i * width, scores_for_date, width, label=date)

    plt.xlabel("Questions")
    plt.ylabel("Scores")
    plt.title(f"Question Responses Over Time for {report_title}")
    plt.xticks(
        x + width / 2,
        [q[:20] + "..." if len(q) > 20 else q for q in questions],
        rotation=45,
        ha="right",
    )
    plt.legend()
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def generate_questions_line_chart(progress_data, report_title):
    """
    Generates a line chart for question responses over time with questions on the X-axis.

    Args:
        progress_data (dict): Dictionary containing question progress data
        report_title (str): Title of the report

    Returns:
        str: The Base64-encoded image.
    """
    plt.figure(figsize=(12, 8))

    # For simplicity, we'll take the first few questions if there are many
    questions = list(progress_data.keys())
    if len(questions) > 5:
        questions = questions[:5]  # Limit to first 5 questions for readability

    # Get shortened question labels for the x-axis
    question_labels = [q[:20] + "..." if len(q) > 20 else q for q in questions]

    # Get unique dates across all questions
    all_dates = []
    for question in questions:
        all_dates.extend(progress_data[question]["dates"])
    unique_dates = sorted(set(all_dates))

    # Limit to first 5 dates if many
    if len(unique_dates) > 5:
        unique_dates = unique_dates[:5]

    # For each date, plot a line across questions
    for date in unique_dates:
        scores_for_date = []

        # Get the score for each question on this date
        for question in questions:
            try:
                date_idx = progress_data[question]["dates"].index(date)
                scores_for_date.append(progress_data[question]["scores"][date_idx])
            except ValueError:
                scores_for_date.append(None)  # No data for this question on this date

        # Filter out None values
        valid_indices = [
            i for i, score in enumerate(scores_for_date) if score is not None
        ]
        if valid_indices:
            valid_questions = [question_labels[i] for i in valid_indices]
            valid_scores = [scores_for_date[i] for i in valid_indices]

            plt.plot(
                valid_questions, valid_scores, marker="o", linestyle="-", label=date
            )

    plt.xlabel("Questions")
    plt.ylabel("Scores")
    plt.title(f"Question Responses Over Time for {report_title}")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(loc="best", title="Dates")
    plt.tight_layout()

    # Save the chart to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    # Encode the image as Base64
    base64_image = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"
