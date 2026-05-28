// Exclusive script for chat.html - Websockets + Other functions

// WEBSOCKETS
// Prevents the browser from restoring scroll position on reload
history.scrollRestoration = "manual";
// Use ws to speed up development, without using VMs
let protocol;
if (location.protocol === "https:") {
    protocol = "wss:";
}
else
{
    protocol = "ws:";
}

// GLOBAL VARIABLES
// Create websocket connection
const ws = new WebSocket(`${protocol}//${location.host}/ws?chat_id=${chatId}`);
const messages = document.getElementById("messages");
const messageText = document.getElementById("messageText");
const chatList = document.querySelector("#chatList");
const sendBtn = document.querySelector("#sendBtn");
const genlinkBtn = document.querySelector("#genlinkBtn");
const activeLinks = document.querySelectorAll(`a[href="/chat?chat_id=${chatId}"]`);
const seeMembers = document.querySelector("#seeMembers");
const memberList = document.querySelector("#memberList");

// Upon connecting, send join message to server
ws.onopen = function() {
    // stringify converts the object to a string, WebSocket only transmits text
    ws.send(JSON.stringify(
        {
            type: "join",
            chatsNotify: chatsNotify
        }
    ))

    let message = document.createElement("li");
    // Create plain text
    let content = document.createTextNode("WebSocket connection established");

    message.appendChild(content);
    messages.appendChild(message);
}

// Show received messages
ws.onmessage = function(event) {

    // Deserialize json
    let payload = JSON.parse(event.data)

    // New message
    if (payload["type"] === "message")
    {
        console.log("ws received", event.data)

        // Current chat: shows message and badge is never updated
        if (payload["chat_id"] === chatId)
        {
            // Format message to HTML

            // If message was sent by current user, align right
            let msgContainer = document.createElement("div")
            msgContainer.classList.add("msgContainer")

            let usernameDiv = document.createElement("div")
            usernameDiv.classList.add("username")
            usernameDiv.textContent = payload["username"]

            let contentDiv = document.createElement("div")
            contentDiv.classList.add("content")
            contentDiv.textContent = payload["content"]

            msgContainer.appendChild(usernameDiv)
            msgContainer.appendChild(contentDiv)

            if (payload["username"] == userName)
            {
                msgContainer.classList.add("flex-row-reverse")
                contentDiv.classList.add("contentSender")
            }

            // Add to DOM
            messages.appendChild(msgContainer);
        }
        // Update badge of the chat that received the message (not the active one)
        else
        {
            // Increment unread message counter
            const chat_id_string = String(payload["chat_id"]);
            unreadCounts[chat_id_string] += 1;

            // Updated chat counter
            const count = unreadCounts[chat_id_string];

            // Modify the DOM
            document.querySelectorAll(`span[data-chat-id="${chat_id_string}"]`).forEach(span => {
                span.textContent = count;

                // No new messages
                if (count === 0)
                {
                    span.style.display = "none";
                }
                // New messages
                else
                {
                    span.style.display = "";
                }
            });

        }

    }
    // Update the member count in the top bar
    else if (payload["type"] === "member_update") {

        document.querySelector("#numMembers").textContent = `Members: ${payload["count"]}`

    }
    // Error
    else if (payload["type"] === "error")
    {
        console.error(payload["content"])
    }

}

// Send message when clicking the button
sendBtn.addEventListener("click", function() {

    // Prevent sending only spaces
    if (!messageText.value.trim())
    {
        return;
    }

    ws.send(JSON.stringify(
        {
            type: "message",
            content: messageText.value
        }
    ));

    // Clear input
    messageText.value = "";

});

// Send message with Enter, Shift+Enter inserts line break without sending
messageText.addEventListener("keydown", function(event) {

    // Prevent sending only spaces
    if (!messageText.value.trim())
    {
        return;
    }

    if (event.key === "Enter" && !event.shiftKey) {

        // Cancel native line break before sending
        event.preventDefault();

        ws.send(JSON.stringify(
            {
                type: "message",
                content: messageText.value
            }
        ));

        // Clear input and reset height
        messageText.value = "";
        messageText.style.height = "auto";
    }
})


// Connection closed: invalid token, inactivity, or network error
ws.onclose = function(event) {
    console.log("Connection closed");
}


// OTHER FUNCTIONS

// Generate private invitation link - button only visible to owner
// Real security verified in backend
if (genlinkBtn) {
    genlinkBtn.addEventListener("click", async function() {

        try{
        
            const response = await fetch(`/chat/${chatId}/invite`, {
                method: "POST",
                // Ensure cookie is sent for post
                credentials: "same-origin"
            })

            // Response with the invitation link URL
            const data = await response.json()

            // Create toast
            const toastEl = document.getElementById("inviteToast");
            document.getElementById("invite-link").textContent = data.invite_url;
            const toast = new bootstrap.Toast(toastEl);
            toast.show();

        }
        catch (error)
        {
            console.log(`Error generating link: ${error.message}`)
        }
        
    });
}

// Send post to update last_seen_at before leaving page
window.addEventListener("beforeunload", function() {
    navigator.sendBeacon(`/chat/${chatId}/seen`);
});


// Change appearance of active chat sidebar
if (activeLinks) {

    activeLinks.forEach(link => {
        link.classList.add("active")
    });

}

// Load and show current chat member list
seeMembers.addEventListener("click", async function() {

    const response = await fetch(`/chat/${chatId}/members`, {
            // GET by default; no data sent
            credentials: "same-origin"
    });

    // Receives JSON object
    const members = await response.json();

    // Clear previous rows before inserting
    memberList.innerHTML = "";

    // Iterate array of dicts
    members.forEach((member, i) => {

        let table_row = document.createElement("tr");
        let table_header = document.createElement("th");
        table_header.scope = "row";
        table_header.textContent = i + 1;

        table_row.appendChild(table_header);

        // Iterate member properties
        for (let clave in member) {

            let table_data = document.createElement("td");
            table_data.textContent = member[clave];       
            
            table_row.appendChild(table_data);

        }

        memberList.appendChild(table_row);
    });

});