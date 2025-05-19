from flask import Flask, request, jsonify, render_template_string, session
from together import Together
from bs4 import BeautifulSoup
from flask_cors import CORS
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import re
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

llm_client = Together(api_key="f19656ccd301f8f3094d4f6a7cb3ba31e2bd3c9cbee0a12141a4f5fdd7541ade")

# Enhanced prompt template for better emotional support
PROMPT_TEMPLATE = (
    "You are a compassionate AI therapist named Wellbeam talking to a user who may be struggling mentally or emotionally. "
    "Use the survey input provided to understand their condition. "
    "Be warm, empathetic, non-judgmental, and encouraging. Provide personalized, actionable suggestions to manage their current state.\n\n"
    "Remember to:\n"
    "- Validate their feelings first before offering solutions\n"
    "- Use a warm, caring tone throughout\n"
    "- Offer specific, practical coping strategies they can try immediately\n"
    "- End with a message of hope and encouragement\n"
    "- If they mention self-harm or suicidal thoughts, emphasize the importance of reaching out to a professional or crisis line\n\n"
    "Survey and Conversation History: {query}\n\n"
    "Respond in HTML with the following structure:\n"
    "- <div id='recipe'>\n"
    "  - <h2 class='name'>Personalized Support for You</h2>\n"
    "  - <p class='validation'>A validating message about their feelings</p>\n"
    "  - <h3>What you can do right now</h3>\n"
    "    <ul class='immediate-actions'>...</ul>\n"
    "  - <h3>Steps to Feel Better</h3>\n"
    "    <ol class='steps'>...</ol>\n"
    "  - <p class='closing'>An encouraging closing message</p>\n"
    "Only return clean, valid HTML with no extra commentary."
)

# Collection of supportive quotes for random display
SUPPORTIVE_QUOTES = [
    "You're braver than you believe, stronger than you seem, and smarter than you think.",
    "The darkest hour has only sixty minutes.",
    "You don't have to see the whole staircase, just take the first step.",
    "Even the darkest night will end and the sun will rise.",
    "You are not alone in this journey. Many have walked this path before and found their way.",
    "Your present circumstances don't determine where you can go; they merely determine where you start.",
    "Healing is not linear. It's okay to have good days and bad days.",
    "Self-care isn't selfish, it's necessary.",
    "Small steps are still steps forward.",
    "You matter. Your story matters. Your voice matters."
]

# HTML template with original intro and enhanced aesthetics
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wellbeam - Your Mental Health Companion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
      /* General Reset */
      body {
        font-family: "Lexend", sans-serif;
        margin: 0;
        padding: 0;
        background: #fdfdfd;
        color: #333;
        line-height: 1.6;
      }

      /* Original Intro Overlay - Preserved as requested */
      #overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #f6f8ff, #e0f7fa);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 999;
        animation: fadeOut 2s ease-in-out 2s forwards;
      }

      .overlay-content {
        text-align: center;
        animation: fadeIn 1s ease-in-out;
      }

      #overlay h1 {
        font-size: 2.5rem;
        margin-bottom: 10px;
      }

      #overlay p {
        font-size: 1.2rem;
        color: #555;
      }

      /* Enhanced Main Content */
      #main-content {
        max-width: 650px;
        margin: 60px auto;
        padding: 30px;
        background-color: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        animation: fadeIn 1s ease-in-out;
      }

      h2 {
        text-align: center;
        margin-bottom: 30px;
        color: #2c3e50;
        font-weight: 600;
      }

      /* Enhanced Form Styles */
      form {
        display: flex;
        flex-direction: column;
        gap: 25px;
      }

      .form-step {
        display: none;
        opacity: 0;
        transition: opacity 0.6s ease;
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        border-left: 4px solid #4cafaa;
      }

      .form-step.active {
        display: block;
        opacity: 1;
      }
      
      .form-step label {
        font-weight: 500;
        color: #2c3e50;
        font-size: 1.1rem;
        display: block;
        margin-bottom: 10px;
      }

      /* Enhanced Inputs & Selects */
      input[type="radio"],
      select,
      textarea {
        margin: 5px 0 10px;
        padding: 12px;
        font-size: 1rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        width: 100%;
        box-sizing: border-box;
        transition: border-color 0.3s, box-shadow 0.3s;
      }
      
      select:focus,
      textarea:focus {
        border-color: #4cafaa;
        box-shadow: 0 0 0 3px rgba(76, 175, 170, 0.2);
        outline: none;
      }

      textarea {
        resize: vertical;
        min-height: 100px;
      }

      button {
        background-color: #4cafaa;
        color: white;
        font-size: 1rem;
        font-weight: 500;
        padding: 14px 28px;
        border: none;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      }

      button:hover {
        background-color: #3a8c91;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
      }
      
      button:active {
        transform: translateY(0);
      }

      /* Enhanced Progress Bar */
      #progress-container {
        height: 10px;
        background-color: #eee;
        border-radius: 10px;
        margin-top: 30px;
        overflow: hidden;
      }

      #progress-bar {
        height: 100%;
        width: 0%;
        background: linear-gradient(to right, #4cafaa, #8bd3dd);
        transition: width 0.5s ease;
        border-radius: 10px;
      }

      /* Navigation buttons */
      .form-navigation {
        display: flex;
        justify-content: space-between;
        margin-top: 25px;
      }
      
      /* Support resources section */
      .support-resources {
        margin-top: 20px;
        padding: 15px;
        background-color: #e8f5e9;
        border-radius: 10px;
        font-size: 0.9rem;
      }
      
      .support-resources h4 {
        margin-top: 0;
        color: #2e7d32;
      }
      
      .support-resources ul {
        margin: 0;
        padding-left: 20px;
      }

      /* Fade Animations */
      @keyframes fadeOut {
        to {
          opacity: 0;
          visibility: hidden;
        }
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      /* Enhanced Radio Button Containers */
      .radio-group {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        padding: 10px 15px;
        border-radius: 8px;
        transition: background-color 0.2s;
        border: 1px solid transparent;
      }
      
      .radio-group:hover {
        background-color: #f0f0f0;
        border-color: #e0e0e0;
      }

      /* Style for the radio button itself */
      .radio-group input[type="radio"] {
        margin-right: 12px;
        width: 18px;
        height: 18px;
        cursor: pointer;
      }

      /* Style for the label text */
      .radio-group label {
        font-size: 1rem;
        color: #333;
        cursor: pointer;
        margin-bottom: 0;
      }

      /* Enhanced Chat UI styles */
      #title-bar {
        background: linear-gradient(135deg, #4cafaa, #8bd3dd);
        color: white;
        padding: 20px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-radius: 20px 20px 0 0;
      }
      
      #title-bar h1 {
        margin: 0;
        font-size: 28px;
      }
      
      #chat-container {
        flex-grow: 1;
        overflow-y: auto;
        padding: 25px;
        display: flex;
        flex-direction: column;
        gap: 18px;
        max-height: 60vh;
        background-color: #f8f9fa;
      }
      
      .message {
        max-width: 80%;
        padding: 15px 20px;
        border-radius: 18px;
        line-height: 1.5;
        box-shadow: 0px 3px 8px rgba(0, 0, 0, 0.08);
        animation: messageIn 0.3s ease-out;
      }
      
      @keyframes messageIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      .user {
        background-color: #d0f0c0;
        align-self: flex-end;
        border-bottom-right-radius: 5px;
      }
      
      .bot {
        background-color: #ffffff;
        align-self: flex-start;
        border-bottom-left-radius: 5px;
        border: 1px solid #e0e0e0;
      }
      
      #input-area {
        display: flex;
        padding: 15px;
        border-top: 1px solid #eee;
        background-color: #fff;
        border-radius: 0 0 20px 20px;
      }
      
      #query {
        flex-grow: 1;
        padding: 15px;
        font-size: 16px;
        border-radius: 25px;
        border: 1px solid #ddd;
        outline: none;
        transition: border-color 0.3s, box-shadow 0.3s;
      }
      
      #query:focus {
        border-color: #4cafaa;
        box-shadow: 0 0 0 3px rgba(76, 175, 170, 0.2);
      }
      
      #send {
        background-color: #4cafaa;
        color: white;
        border: none;
        padding: 12px 24px;
        margin-left: 10px;
        border-radius: 25px;
        cursor: pointer;
        font-size: 16px;
        transition: all 0.3s;
      }
      
      #send:hover {
        background-color: #3a8c91;
        transform: translateY(-2px);
      }
      
      /* Enhanced recipe display styling */
      #recipe-display h2.name {
        color: #4cafaa;
        font-size: 24px;
        margin-bottom: 15px;
        border-bottom: 2px solid #e0f7fa;
        padding-bottom: 10px;
      }
      
      #recipe-display p.validation {
        font-style: italic;
        color: #555;
        background-color: #f5f5f5;
        padding: 10px 15px;
        border-radius: 8px;
        border-left: 3px solid #4cafaa;
        margin-bottom: 20px;
      }
      
      #recipe-display h3 {
        color: #2c3e50;
        font-size: 20px;
        margin-top: 20px;
      }
      
      #recipe-display ul.immediate-actions,
      #recipe-display ol.steps {
        margin-left: 20px;
        padding-left: 20px;
      }
      
      #recipe-display li {
        margin-bottom: 12px;
        line-height: 1.6;
      }
      
      #recipe-display p.closing {
        margin-top: 20px;
        font-weight: 600;
        color: #4cafaa;
        text-align: center;
        padding: 10px;
        border-top: 1px solid #e0f7fa;
      }
      
      #chat-ui {
        margin: 0px 0px;
        padding: 0;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        background: #fff;
        overflow: hidden;
      }
      
      /* Breathing exercise animation */
      .breathing-guide {
        width: 100px;
        height: 100px;
        background-color: #4cafaa;
        border-radius: 50%;
        margin: 20px auto;
        animation: breathe 8s infinite ease-in-out;
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 14px;
        text-align: center;
      }
      
      @keyframes breathe {
        0%, 100% {
          transform: scale(0.8);
          background-color: #4cafaa;
        }
        50% {
          transform: scale(1.2);
          background-color: #8bd3dd;
        }
      }
      
      /* Responsive design improvements */
      @media (max-width: 768px) {
        #overlay h1 {
          font-size: 2.2rem;
        }
        
        #overlay p {
          font-size: 1.1rem;
        }
        
        #main-content, #chat-ui {
          margin: 0px;
          padding: 20px 15px;
        }
        
        .message {
          max-width: 90%;
        }
      }

      /* Enhanced recipe styling */
      #recipe {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
      }
      
      #recipe h2.name {
        color: #ff5e62;
        font-size: 24px;
        margin-bottom: 15px;
        text-align: center;
      }
      
      #recipe h3 {
        color: #444;
        font-size: 18px;
        margin-top: 20px;
        padding-bottom: 5px;
        border-bottom: 1px solid #f0f0f0;
      }
      
      #recipe ul.ingredients,
      #recipe ol.steps {
        margin-left: 20px;
        padding-left: 20px;
      }
      
      #recipe li {
        margin-bottom: 12px;
        line-height: 1.6;
      }
      
      #recipe p.closing {
        margin-top: 20px;
        font-style: italic;
        color: #4cafaa;
        text-align: center;
        padding: 10px;
        background-color: #f9f9f9;
        border-radius: 8px;
      }
    </style>
  </head>
  <body>
    <div id="overlay">
      <div class="overlay-content">
        <h1>Welcome to Wellbeam 🌞</h1>
        <p>Your mental wellness companion</p>
      </div>
    </div>

    <div id="main-content" style="display: none">
      <h2>Let's check in with you today 💬</h2>
      <p style="text-align: center; margin-bottom: 25px; color: #666;">Your responses help us provide personalized support. Take your time.</p>

      <form id="mood-form">
        <!-- Step 1 -->
        <div class="form-step active" data-step="1">
          <label>How would you describe your mood today?</label><br />
          <div class="radio-group">
            <input
              type="radio"
              name="mood"
              value="Happy"
              id="mood-happy"
              required
            />
            <label for="mood-happy">Happy</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="mood" value="Sad" id="mood-sad" />
            <label for="mood-sad">Sad</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="mood" value="Anxious" id="mood-anxious" />
            <label for="mood-anxious">Anxious</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="mood" value="Angry" id="mood-angry" />
            <label for="mood-angry">Angry</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="mood" value="Neutral" id="mood-neutral" />
            <label for="mood-neutral">Neutral</label>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="form-step" data-step="2">
          <label>How well did you sleep last night?</label><br />
          <select name="sleep" required>
            <option value="">-- Select --</option>
            <option value="Very well">Very well (7+ hours)</option>
            <option value="Okay">Okay (5-6 hours)</option>
            <option value="Poorly">Poorly (3-4 hours)</option>
            <option value="Didn't sleep">Didn't sleep much (0-2 hours)</option>
          </select>
        </div>

        <!-- Step 3 -->
        <div class="form-step" data-step="3">
          <label>How is your energy level today?</label><br />
          <select name="energy" required>
            <option value="">-- Select --</option>
            <option value="High">High - I feel energetic</option>
            <option value="Moderate">Moderate - I'm doing okay</option>
            <option value="Low">Low - I feel tired</option>
            <option value="Exhausted">Exhausted - I can barely function</option>
          </select>
        </div>

        <!-- Step 4 -->
        <div class="form-step" data-step="4">
          <label>How many people have you interacted with today?</label><br />
          <select name="social" required>
            <option value="">-- Select --</option>
            <option value="None">None - I've been alone</option>
            <option value="1-2">1-2 people</option>
            <option value="3-5">3-5 people</option>
            <option value="More than 5">More than 5 people</option>
          </select>
        </div>

        <!-- Step 5 -->
        <div class="form-step" data-step="5">
          <label>Have you had any thoughts of self-harm or suicide?</label><br />
          <div class="radio-group">
            <input
              type="radio"
              name="suicidal"
              value="No"
              id="suicidal-no"
              required
            />
            <label for="suicidal-no">No</label>
          </div>
          <div class="radio-group">
            <input
              type="radio"
              name="suicidal"
              value="Yes, occasionally"
              id="suicidal-occasionally"
            />
            <label for="suicidal-occasionally">Yes, occasionally</label>
          </div>
          <div class="radio-group">
            <input
              type="radio"
              name="suicidal"
              value="Yes, frequently"
              id="suicidal-frequently"
            />
            <label for="suicidal-frequently">Yes, frequently</label>
          </div>
          <div class="support-resources">
            <h4>Support Resources</h4>
            <ul>
              <li>National Suicide Prevention Lifeline: 988 or 1-800-273-8255</li>
              <li>Crisis Text Line: Text HOME to 741741</li>
            </ul>
          </div>
        </div>

        <!-- Step 6 -->
        <div class="form-step" data-step="6">
          <label>How is your appetite?</label><br />
          <select name="appetite" required>
            <option value="">-- Select --</option>
            <option value="Normal">Normal - eating regular meals</option>
            <option value="Low">Low - not very hungry</option>
            <option value="High">High - eating more than usual</option>
            <option value="No appetite at all">No appetite at all</option>
          </select>
        </div>

        <!-- Step 7 -->
        <div class="form-step" data-step="7">
          <label>Have you felt stressed or overwhelmed today?</label><br />
          <div class="radio-group">
            <input
              type="radio"
              name="stress"
              value="Yes, very much"
              id="stress-very"
              required
            />
            <label for="stress-very">Yes, very much</label>
          </div>
          <div class="radio-group">
            <input
              type="radio"
              name="stress"
              value="Yes, somewhat"
              id="stress-somewhat"
            />
            <label for="stress-somewhat">Yes, somewhat</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="stress" value="No" id="stress-no" />
            <label for="stress-no">No, I'm managing well</label>
          </div>
        </div>

        <!-- Step 8 -->
        <div class="form-step" data-step="8">
          <label>Have you taken time for yourself today?</label><br />
          <div class="radio-group">
            <input
              type="radio"
              name="selfcare"
              value="Yes, quality time"
              id="selfcare-quality"
              required
            />
            <label for="selfcare-quality">Yes, quality time</label>
          </div>
          <div class="radio-group">
            <input
              type="radio"
              name="selfcare"
              value="Yes, a little"
              id="selfcare-little"
            />
            <label for="selfcare-little">Yes, a little</label>
          </div>
          <div class="radio-group">
            <input type="radio" name="selfcare" value="No" id="selfcare-no" />
            <label for="selfcare-no">No, not yet</label>
          </div>
        </div>

        <!-- Step 9 -->
        <div class="form-step" data-step="9">
          <label>Is there anything specific on your mind today?</label><br />
          <textarea name="thoughts" rows="4" placeholder="Feel free to share what's on your mind. This helps us provide better support."></textarea>
          <p style="font-size: 0.9rem; color: #666; margin-top: 10px;">Your thoughts are safe with us. We're here to help.</p>
        </div>

        <!-- Navigation buttons -->
        <div class="form-navigation">
          <button type="button" id="prev-btn" style="display: none">
            Previous
          </button>
          <button type="button" id="next-btn">Next</button>
        </div>

        <!-- Progress Bar -->
        <div id="progress-container">
          <div id="progress-bar"></div>
        </div>
      </form>
    </div>

    <!-- Chat UI (initially hidden) -->
    <div id="chat-ui" style="display: none">
      <div id="title-bar">
        <h1>Wellbeam</h1>
        <span>Caring for your mind</span>
      </div>
      <div id="chat-container"></div>
      <form id="input-area">
        <input
          type="text"
          id="query"
          placeholder="Type your thoughts here..."
          autocomplete="off"
        />
        <button type="submit" id="send">Send</button>
      </form>
    </div>

   <script>
  window.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);

    const patientId = params.get("patientId");
    const name = params.get("name");
    const phoneNumber = params.get("phoneNumber");
    const guardianPhoneNumber = params.get("guardianPhoneNumber");
    const email = params.get("email");

    if (patientId && name && phoneNumber && guardianPhoneNumber && email) {
      localStorage.setItem("patientId", patientId);
      localStorage.setItem("patientName", name);
      localStorage.setItem("patientPhoneNumber", phoneNumber);
      localStorage.setItem("patientGuardianPhoneNumber", guardianPhoneNumber);
      localStorage.setItem("patientEmail", email);
      console.log("[LocalStorage] Patient data restored after redirect ✅");
    } else {
      console.warn("Missing one or more patient details in URL. Skipping localStorage.");
    }
  });

  // Wait for the overlay to finish animating (2s delay + 2s duration)
  setTimeout(() => {
    document.getElementById("main-content").style.display = "block";
  }, 4000);

  // Form navigation logic
  let currentStep = 1;
  const totalSteps = 9;
  const form = document.getElementById("mood-form");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const progressBar = document.getElementById("progress-bar");
  const chatContainer = document.getElementById("chat-container");
  const inputArea = document.getElementById("input-area");
  const queryInput = document.getElementById("query");
  const chatUI = document.getElementById("chat-ui");

  function updateForm() {
    // Hide all steps
    document.querySelectorAll(".form-step").forEach((step) => {
      step.classList.remove("active");
    });

    // Show current step
    document
      .querySelector(`.form-step[data-step="${currentStep}"]`)
      .classList.add("active");

    // Update progress bar
    progressBar.style.width = `${(currentStep / totalSteps) * 100}%`;

    // Update buttons
    prevBtn.style.display = currentStep === 1 ? "none" : "block";
    nextBtn.textContent = currentStep === totalSteps ? "Submit" : "Next";
  }

  function validateStep() {
    const currentStepElement = document.querySelector(
      `.form-step[data-step="${currentStep}"]`
    );
    const inputs = currentStepElement.querySelectorAll(
      "input[required], select[required]"
    );

    for (let input of inputs) {
      if (input.type === "radio" || input.type === "checkbox") {
        const checked = currentStepElement.querySelector(
          `input[name="${input.name}"]:checked`
        );
        if (!checked) return false;
      } else if (!input.value) {
        return false;
      }
    }
    return true;
  }

  function appendMessage(htmlContent, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender);
    messageDiv.innerHTML = htmlContent;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  nextBtn.addEventListener("click", () => {
    if (!validateStep()) {
      alert("Please answer the question before proceeding.");
      return;
    }

    if (currentStep < totalSteps) {
      currentStep++;
      updateForm();
    } else {
      // Handle form submission - get all values
      const formData = new FormData(form);
      const surveySummary = `Mood: ${formData.get(
        "mood"
      )}, Sleep: ${formData.get("sleep")}, Energy: ${formData.get(
        "energy"
      )}, Social: ${formData.get(
        "social"
      )}, Suicidal thoughts: ${formData.get(
        "suicidal"
      )}, Appetite: ${formData.get("appetite")}, Stress: ${formData.get(
        "stress"
      )}, Self-care: ${formData.get("selfcare")}, Thoughts: ${
        formData.get("thoughts") || "None shared"
      }`;

      // Add patient data from localStorage
      const patientData = {
        patientId: localStorage.getItem("patientId") || "",
        patientName: localStorage.getItem("patientName") || "",
        patientPhoneNumber: localStorage.getItem("patientPhoneNumber") || "",
        patientGuardianPhoneNumber: localStorage.getItem("patientGuardianPhoneNumber") || "",
        patientEmail: localStorage.getItem("patientEmail") || ""
      };

      // Hide form, show chat UI
      document.getElementById("main-content").style.display = "none";
      chatUI.style.display = "block";

      appendMessage("<b>Survey Submitted:</b><br>" + surveySummary, "user");
      appendMessage("<div class='breathing-guide'>Analyzing your responses...</div>", "bot");

      // Send data to backend
      fetch("/generate_response", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "PatientId": patientData.patientId,
          "PatientName": patientData.patientName,
          "PatientPhone": patientData.patientPhoneNumber,
          "PatientGuardianPhone": patientData.patientGuardianPhoneNumber,
          "PatientEmail": patientData.patientEmail
        },
        body: JSON.stringify({ 
          query: surveySummary,
          patientData: patientData
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          // Remove the "thinking" message
          const botMessages = document.getElementsByClassName("bot");
          botMessages[botMessages.length - 1].remove();
          // Add the real response
          appendMessage(data.html, "bot");
        })
        .catch((error) => {
          console.error("Error:", error);
          appendMessage(
            "I'm sorry, there was an error processing your responses. Please try again later or reach out to your healthcare provider directly.",
            "bot"
          );
        });
    }
  });

  prevBtn.addEventListener("click", () => {
    if (currentStep > 1) {
      currentStep--;
      updateForm();
    }
  });

  // Handle chat input after survey
  if (document.getElementById("input-area")) {
    document
      .getElementById("input-area")
      .addEventListener("submit", async (e) => {
        e.preventDefault();
        const queryText = queryInput.value.trim();
        if (!queryText) return;
        appendMessage(queryText, "user");
        queryInput.value = "";
        appendMessage("<div class='breathing-guide'>Thinking...</div>", "bot");

        try {
          const response = await fetch("/generate_response", {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "PatientId": localStorage.getItem("patientId") || "",
              "PatientName": localStorage.getItem("patientName") || "",
              "PatientPhone": localStorage.getItem("patientPhoneNumber") || "",
              "PatientGuardianPhone": localStorage.getItem("patientGuardianPhoneNumber") || "",
              "PatientEmail": localStorage.getItem("patientEmail") || ""
            },
            body: JSON.stringify({ query: queryText }),
          });

          const data = await response.json();
          const botMessages = document.getElementsByClassName("bot");
          botMessages[botMessages.length - 1].remove();
          appendMessage(data.html, "bot");
        } catch (error) {
          console.error("Error:", error);
          appendMessage(
            "I'm sorry, I'm having trouble responding right now. Please try again or reach out to your healthcare provider if you need immediate support.",
            "bot"
          );
        }
      });
  }

  // Initialize form
  updateForm();
</script>
</body>
</html>

"""

def extract_recipe_html(text):
    cleaned_text = re.sub(r'<Thinking>.*?</Thinking>', '', text, flags=re.DOTALL)
    cleaned_text = re.sub(r'(html)?\n', '', cleaned_text).strip().rstrip('')
    soup = BeautifulSoup(cleaned_text, 'html.parser')
    recipe_div = soup.find('div', id='recipe')
    return str(recipe_div) if recipe_div else cleaned_text

def store_survey_in_firebase(survey_data, request):
    try:
        # Get patient data from both request headers and JSON body
        patient_data = {}
        
        # Try to get from JSON body first
        req_data = request.get_json()
        if req_data and "patientData" in req_data:
            patient_data = {
                'patientEmail': req_data["patientData"].get('patientEmail', ''),
                'patientGuardianPhoneNumber': req_data["patientData"].get('patientGuardianPhoneNumber', ''),
                'patientId': req_data["patientData"].get('patientId', ''),
                'patientName': req_data["patientData"].get('patientName', ''),
                'patientPhoneNumber': req_data["patientData"].get('patientPhoneNumber', '')
            }
        
        # If any value is still empty, try headers
        if not all(patient_data.values()):
            headers_data = {
                'patientEmail': request.headers.get('PatientEmail', ''),
                'patientGuardianPhoneNumber': request.headers.get('PatientGuardianPhone', ''),
                'patientId': request.headers.get('PatientId', ''),
                'patientName': request.headers.get('PatientName', ''),
                'patientPhoneNumber': request.headers.get('PatientPhone', '')
            }
            
            # Replace empty values with header values
            for key, value in patient_data.items():
                if not value and headers_data[key]:
                    patient_data[key] = headers_data[key]
        
        # Log patient data for debugging
        print("Patient data to be stored:", patient_data)
        
        # Combine all data
        full_data = {
            **survey_data,
            **patient_data,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'session_id': session.get('session_id', '')
        }
        
        # Add follow-up flag based on survey responses
        if survey_data.get('suicidal', '').startswith('Yes') or survey_data.get('mood', '') == 'Sad':
            full_data['needs_followup'] = True
        
        doc_ref = db.collection('survey_responses').document()
        doc_ref.set(full_data)
        
        # If this is a new session, store the session ID
        if 'session_id' not in session:
            session['session_id'] = doc_ref.id
            
        return True
    except Exception as e:
        print(f"Error storing survey in Firebase: {e}")
        return False

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate_response', methods=['POST'])
def generate_response():
    req_data = request.get_json()
    if not req_data or "query" not in req_data:
        return jsonify({"error": "Please provide a 'query' field in JSON format."}), 400

    user_query = req_data["query"]
    
    # Check if this is a survey submission
    if all(field in user_query for field in ["Mood:", "Sleep:", "Energy:", "Social:", "Suicidal thoughts:", "Appetite:", "Stress:", "Self-care:"]):
        try:
            # Parse survey data
            survey_data = {}
            parts = [part.strip() for part in user_query.split(',')]
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    clean_key = key.strip().lower().replace('-', '').replace(' ', '_')
                    survey_data[clean_key] = value.strip()
            
            # Store in Firebase with patient data
            if not store_survey_in_firebase(survey_data, request):
                return jsonify({"error": "Failed to save survey data"}), 500
            
            # Check for critical responses that might need immediate attention
            is_critical = False
            critical_message = ""
            
            if "yes, frequently" in survey_data.get('suicidal', '').lower():
                is_critical = True
                critical_message = "I notice you mentioned having frequent thoughts of self-harm. Your wellbeing is important, and I strongly encourage you to reach out to a mental health professional or crisis line right away."
            
            # Continue with conversation
            if "conversation" not in session:
                session["conversation"] = []

            session["conversation"].append(f"User: {user_query}")
            
            # Add context about the user's state for better personalization
            context_notes = ""
            if is_critical:
                context_notes = f"\n\nIMPORTANT: This user has indicated {survey_data.get('suicidal', '')} thoughts of self-harm or suicide. Provide compassionate support and strongly encourage professional help."
            
            recent_context = session["conversation"][-8:]
            full_context = "\n".join(recent_context) + context_notes

            response = llm_client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=full_context)}],
                temperature=0.5
            )
            generated_text = response.choices[0].message.content
            
            # If critical, prepend the critical message
            if is_critical:
                soup = BeautifulSoup(extract_recipe_html(generated_text), 'html.parser')
                if soup.find('div', id='recipe'):
                    validation_p = soup.find('p', class_='validation')
                    if validation_p:
                        validation_p.string = critical_message + " " + (validation_p.string or "")
                    else:
                        new_p = soup.new_tag('p', attrs={'class': 'validation'})
                        new_p.string = critical_message
                        soup.find('div', id='recipe').insert(1, new_p)
                    generated_text = str(soup)
            
            session["conversation"].append(f"Assistant: {generated_text}")

            return jsonify({"html": extract_recipe_html(generated_text)}), 200

        except Exception as e:
            print(f"Survey processing error: {e}")
            return jsonify({"error": "Failed to process survey", "details": str(e)}), 500
    
    # Handle regular chat messages
    else:
        if "conversation" not in session:
            session["conversation"] = []

        session["conversation"].append(f"User: {user_query}")
        recent_context = session["conversation"][-8:]
        full_context = "\n".join(recent_context)

        try:
            response = llm_client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=full_context)}],
                temperature=0.5
            )
            generated_text = response.choices[0].message.content
            session["conversation"].append(f"Assistant: {generated_text}")
            return jsonify({"html": extract_recipe_html(generated_text)}), 200
        except Exception as e:
            print(f"LLM error: {e}")
            return jsonify({"error": "LLM service failure", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)