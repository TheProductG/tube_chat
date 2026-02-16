document.addEventListener('DOMContentLoaded', () => {
    const youtubeUrlInput = document.getElementById('youtube-url');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loader = document.getElementById('loader');
    const contentGrid = document.getElementById('content-grid');
    const summaryContent = document.getElementById('summary-content');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    let currentTranscript = '';
    let currentVideoId = '';
    let chatHistory = [];

    // Analyze Video
    analyzeBtn.addEventListener('click', async () => {
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            alert('Please enter a YouTube URL');
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.innerText = 'Analyzing...';
        loader.classList.remove('hidden');
        contentGrid.classList.add('hidden');

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to analyze video');
            }

            currentTranscript = data.transcript;
            currentVideoId = data.video_id;

            // Format Summary
            let summaryHTML = formatMarkdown(data.summary);
            if (data.cached) {
                summaryHTML = `<div class="cache-badge">Cached Analysis</div>` + summaryHTML;
            }
            summaryContent.innerHTML = summaryHTML;

            // Show interface
            loader.classList.add('hidden');
            contentGrid.classList.remove('hidden');

            // Initial msg
            chatMessages.innerHTML = `
                <div class="message bot-message">
                    <div class="bubble">I've analyzed the video! Feel free to ask me anything specific about what was discussed.</div>
                </div>
            `;
            chatHistory = [];

        } catch (error) {
            alert(error.message);
            loader.classList.add('hidden');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerText = 'Summarize';
        }
    });

    // Send Message
    async function sendMessage() {
        const question = userInput.value.trim();
        if (!question || !currentTranscript) return;

        appendMessage('user', question);
        userInput.value = '';

        const loadingMsg = appendMessage('bot', '<div class="spinner-small"></div> Reading transcript...', true);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_id: currentVideoId,
                    question: question,
                    history: chatHistory
                })
            });

            const data = await response.json();
            loadingMsg.remove();

            if (!response.ok) throw new Error('Failed to get answer');

            appendMessage('bot', data.answer);

            chatHistory.push({ role: 'user', content: question });
            chatHistory.push({ role: 'assistant', content: data.answer });

        } catch (error) {
            loadingMsg.innerHTML = '<div class="bubble error">Sorry, I encountered an error. Please try again.</div>';
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function appendMessage(role, content, isHtml = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-message`;
        msgDiv.innerHTML = `<div class="bubble">${content}</div>`;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^\s*[-*]\s+(.*)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
    }
});
