const API_BASE = window.location.origin;

const fileInput = document.getElementById("fileInput");
const uploadButton = document.getElementById("uploadButton");
const fileInfo = document.getElementById("fileInfo");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const fileStatus = document.getElementById("fileStatus");
const clearFile = document.getElementById("clearFile");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");
const landingPage = document.getElementById("landingPage");
const uploadPanel = document.getElementById("uploadPanel");
const chatPanel = document.getElementById("chatPanel");
const uploadOption = document.getElementById("uploadOption");
const chatOption = document.getElementById("chatOption");
const backButton = document.querySelector(".back-button");
const chatBackButton = document.getElementById("chatBackButton");
const appShell = document.querySelector(".app-shell");

uploadOption.addEventListener("click", () => fileInput.click());
chatOption.addEventListener("click", () => showPanel("chat"));
backButton.addEventListener("click", showLanding);
chatBackButton.addEventListener("click", showLanding);

uploadButton.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", handleFileSelect);
clearFile.addEventListener("click", clearSelectedFile);
chatForm.addEventListener("submit", handleChatSubmit);

// Ensure the landing state is correct on page load
showLanding();

function showPanel(type, skipWelcome = false) {
  landingPage.classList.add("hidden");
  if (type === "upload") {
    uploadPanel.classList.remove("hidden");
    chatPanel.classList.add("hidden");
    chatForm.classList.add("hidden");
    chatBackButton.classList.add("hidden");
    appShell.classList.remove("chat-mode");
  } else if (type === "chat") {
    uploadPanel.classList.add("hidden");
    chatPanel.classList.remove("hidden");
    chatForm.classList.remove("hidden");
    chatBackButton.classList.remove("hidden");
    appShell.classList.add("chat-mode"); // Clear previous messages
    if (!skipWelcome) {
      generateWelcomeMessage();
    }
  }
  backButton.style.display = "grid";
}

function showLanding() {
  landingPage.classList.remove("hidden");
  uploadPanel.classList.add("hidden");
  chatPanel.classList.add("hidden");
  chatForm.classList.add("hidden");
  chatBackButton.classList.add("hidden");
  appShell.classList.remove("chat-mode");
  backButton.style.display = "none";
}

function handleFileSelect() {
  const file = fileInput.files[0];
  if (!file) {
    clearSelectedFile();
    return;
  }

  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  fileInfo.classList.remove("hidden");
  fileStatus.textContent = "Uploading file to server...";
  fileStatus.classList.remove("hidden");
  uploadPrescription(file);
}

function clearSelectedFile() {
  fileInput.value = "";
  fileInfo.classList.add("hidden");
  fileStatus.classList.add("hidden");
  fileName.textContent = "";
  fileSize.textContent = "";
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage(text, "user");
  chatInput.value = "";
  chatInput.focus();

  appendTypingIndicator();
  const sendButton = document.querySelector(".send-button");
  sendButton.disabled = true;

  try {
    const medicine = await searchMedicine(text);
    if (medicine && medicine.score >= 70) {
      const response = await fetch(`${API_BASE}/medicine?name=${encodeURIComponent(medicine.name)}`);
      if (!response.ok) {
        throw new Error(`Medicine lookup failed: ${response.status}`);
      }
      const fullData = await response.json();
      if (fullData.matched && fullData.medicine) {
        appendMessage(formatMedicineDetails(fullData), "bot");
      } else if (fullData.suggestions?.length) {
        appendMessage(formatSuggestionMessage(fullData.suggestions), "bot");
      } else {
        appendMessage("I found a medicine name but could not retrieve details.", "bot");
      }
    } else {
      const response = await chatWithServer(text);
      appendMessage(response, "bot");
    }
  } catch (error) {
    console.error(error);
    appendMessage("Sorry, I couldn't process your request. Please try again.", "bot");
  } finally {
    removeTypingIndicator();
    sendButton.disabled = false;
  }
}

function appendMessage(text, sender) {
  const messageElement = document.createElement("div");
  messageElement.className = `message ${sender}-message`;

  const bubble = document.createElement("span");
  bubble.className = "bubble";
  bubble.innerHTML = text.replace(/\n/g, "<br>");
  messageElement.appendChild(bubble);
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function uploadPrescription(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE}/upload-prescription`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    const data = await response.json();
    fileStatus.textContent = `Uploaded ${data.filename} (${formatBytes(data.size_bytes)}), extracted ${data.extracted_text_length} characters`;
    fileStatus.classList.remove("hidden");

    // After successful upload, switch to chat mode
    setTimeout(() => {
      showPanel("chat", true);
      appendMessage(`I've uploaded your prescription "${data.filename}". How can I help you with it?`, "bot");
    }, 1500); // Give user time to see the upload confirmation

  } catch (error) {
    console.error(error);
    fileStatus.textContent = "Upload failed. Please try again.";
    fileStatus.classList.remove("hidden");
  }
}

function formatMedicineDetails(response) {
  const med = response.medicine;
  const lines = [];
  lines.push(`${med.name} — ${med.category}`);
  lines.push(`Prescription required: ${med.prescription_required ? "Yes" : "No"}`);
  if (med.manufacturer) lines.push(`Manufacturer: ${med.manufacturer}`);
  if (med.composition) lines.push(`Composition: ${med.composition}`);
  if (med.mrp) lines.push(`MRP: ${med.mrp}`);
  if (med.availability) lines.push(`Availability: ${med.availability}`);
  if (med.uses) lines.push(`Uses: ${med.uses.join(", ")}`);
  if (med.side_effects) lines.push(`Side effects: ${med.side_effects.join(", ")}`);
  if (med.alternate_medicines) lines.push(`Alternatives: ${med.alternate_medicines.join(", ")}`);
  if (med.how_to_use) lines.push(`How to use: ${med.how_to_use}`);
  if (response.suggestions?.length) {
    lines.push("Suggestions:");
    lines.push(response.suggestions.map(s => `• ${s.name} (${s.score})`).join("\n"));
  }
  return lines.join("\n");
}

function formatSuggestionMessage(suggestions) {
  const lines = [
    "I couldn't identify a single exact medicine. Here are some close matches:",
    ...suggestions.map((hit, index) => `${index + 1}. ${hit.name} (${hit.score})`),
    "You can try one of these names or ask a different question.",
  ];
  return lines.join("\n");
}

// ------------------------------
// CHAT HISTORY MEMORY
// ------------------------------
const chatHistory = [
  {
    role: "system",
    content: `
You are an AI pharmaceutical assistant.

Rules:
- Give medicine-related informational guidance only.
- Never diagnose diseases.
- Never replace doctors.
- Always suggest consulting a healthcare professional.
- Keep responses short and clear.
`
  }
];

// ------------------------------
// MEDICINE SEARCH FUNCTION
// ------------------------------
async function searchMedicine(query) {
  try {
    const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=1`);
    if (!response.ok) return null;
    const data = await response.json();
    return data.length > 0 ? data[0] : null;
  } catch (e) {
    console.error(e);
    return null;
  }
}

// ------------------------------
// GPT RESPONSE FUNCTION
// ------------------------------
async function chatWithServer(message) {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    return data.reply || "Sorry, I couldn't get an answer from the server.";
  } catch (error) {
    console.error("Chat proxy error:", error);
    return "Sorry, the chat server is unavailable right now.";
  }
}

function appendTypingIndicator() {
  const indicator = document.createElement("div");
  indicator.className = "message bot-message typing-indicator";
  indicator.innerHTML = '<span class="bubble">Typing...</span>';
  chatMessages.appendChild(indicator);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
  const indicator = document.querySelector(".typing-indicator");
  if (indicator) {
    indicator.remove();
  }
}

function generateWelcomeMessage() {
  appendTypingIndicator();
  setTimeout(() => {
    removeTypingIndicator();
    appendMessage("Hello! I'm your AI Prescription Assistant. You can ask medicine-related questions or upload prescriptions for analysis.", "bot");
  }, 500);
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(2))} ${sizes[i]}`;
}