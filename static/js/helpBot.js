(() => {
  // ===============================
  // Phil's AI Floating Assistant v2
  // Advanced UI + Effects + Typing
  // ===============================

  const KB = [

{
q: /(HI|Hello|Hey|Whats up|WhatsApp|Good morning|Good afternoon|Good evening)/i,
a: ["Hello! How can I help you today?", "Hi there! What can I do for you?", "Hey! How's it going?"],
},
{
q: /(How are you|How’s it going|How do you do|Are you doing well)/i,
a: ["I am doing great, thank you! How are you?", "I am up and running perfectly. How can I assist you?"],
},
{
q: /(Thank you|Thanks|Thank you so much|Appreciate it)/i,
a: ["You're very welcome!", "Anytime! Happy to help.", "Glad I could be of assistance."],
},
{
q: /(Goodbye|Bye|See you later|I am leaving|Good night)/i,
a: ["Goodbye! Have a wonderful day.", "See you later! Take care.", "Bye! Feel free to reach out if you need anything else."],
},
{
q: /(Nice to meet you|Pleased to meet you)/i,
a: ["Nice to meet you too! How can I help you today?", "The pleasure is mine!"],
},
{
q: /(What is up|Sup|What's cracking)/i,
a: ["Not much, just here and ready to help you! What's on your mind?", "All systems stable! How can I help?"],
},
{
q: /(Sorry|I apologize|My bad)/i,
a: ["No need to apologize at all!", "No worries! Let's keep going."],
},
{
q: /(Are you there|Anyone home|Hellooo)/i,
a: ["Yes, I am here! How can I assist you?", "Present! What do you need help with?"],
},

{
q: /(Awesome|Great|Perfect|Cool|Wonderful)/i,
a: ["Awesome! Let me know if you need anything else.", "Great! I am glad you think so."],
},

{
q: /(No thank you|No thanks|I am good|That is all)/i,
a: ["Alright! Have a great day ahead.", "Perfect. Let me know if you need anything later."]
},




 {
    q: /(HI|Hello|Hey|Whats up|WhatsApp)/i,
    a: ["Hello! How can I help you today.", "Hi there! What can I do for you?", "Hey! How's it going?"]
  },
  {
    q: /(Good morning)/i,
    a: ["Good morning! I hope you are having a great day.", "Morning! How can I assist you today?"]
  },
  {
    q: /(Good afternoon)/i,
    a: ["Good afternoon! How can I help you right now?", "Afternoon! What can I look up for you?"]
  },
  {
    q: /(Good evening)/i,
    a: ["Good evening! How can I assist you tonight?", "Evening! What can I help you with?"]
  },
  {
    q: /(How are you|How is it going|How do you do)/i,
    a: ["I am doing great, thank you! How are you?", "I am up and running perfectly. How can I assist you?"]
  },
  {
    q: /(Are you doing well|How are things)/i,
    a: ["Everything is running smoothly over here! How about you?", "Doing well! Ready to solve your problems."]
  },
  {
    q: /(Thank you|Thanks|Thank you so much)/i,
    a: ["You're very welcome!", "Anytime! Happy to help.", "Glad I could be of assistance."]
  },
  {
    q: /(Appreciate it|Much appreciated)/i,
    a: ["Happy to help anytime!", "You are very welcome!", "No problem at all!"]
  },
  {
    q: /(Goodbye|Bye|See you later)/i,
    a: ["Goodbye! Have a wonderful day.", "See you later! Take care.", "Bye! Feel free to reach out later."]
  },
  {
    q: /(I am leaving|Good night)/i,
    a: ["Good night! Sleep well.", "Have a great evening! See you next time."]
  },
  {
    q: /(Nice to meet you|Pleased to meet you)/i,
    a: ["Nice to meet you too! How can I help you today?", "The pleasure is mine!"]
  },
  {
    q: /(What is up|Sup|What is cracking)/i,
    a: ["Not much, just here and ready to help you! What's on your mind?", "All systems stable! How can I help?"]
  },
  {
    q: /(Sorry|I apologize|My bad)/i,
    a: ["No need to apologize at all!", "No worries! Let's keep going.", "It is totally fine!"]
  },
  {
    q: /(Are you there|Anyone home|Hellooo)/i,
    a: ["Yes, I am here! How can I assist you?", "Present! What do you need help with?"]
  },
  {
    q: /(Awesome|Great|Perfect|Cool|Wonderful)/i,
    a: ["Awesome! Let me know if you need anything else.", "Great! I am glad you think so."]
  },
  {
    q: /(No thank you|No thanks|I am good)/i,
    a: ["Alright! Have a great day ahead.", "Perfect. Let me know if you need anything later."]
  },
  {
    q: /(That is all|Nothing else)/i,
    a: ["Understood. Have an amazing day!", "Got it. Feel free to open a new chat whenever."]
  },
  {
    q: /(Please help me|I need help|Assist me)/i,
    a: ["I am here for you! Tell me what you need.", "Absolutely. What seems to be the problem?"]
  },
  {
    q: /(Yo|Hru|Sup bot)/i,
    a: ["Yo! What is going on?", "Hey there! Ready when you are."]
  },
  {
    q: /(Long time no see|I am back)/i,
    a: ["Welcome back! How can I assist you today?", "Great to see you again! What is on your mind?"]
  },
  {
    q: /(Testing|Test bot|Check check)/i,
    a: ["System test successful! I am listening.", "Testing clear. All networks are online!"]
  },
  {
    q: /(Thank you bot|Good bot|Nice bot)/i,
    a: ["That is what I am here for!", "Thank you! I try my absolute best."]
  },
  {
    q: /(Bad bot|You are useless|Terrible bot)/i,
    a: ["I am sorry to hear that. Let me know how I can improve.", "My apologies. I am trying to learn."]
  },
  {
    q: /(Excuse me)/i,
    a: ["Yes? How can I assist you?", "Hello! What can I do for you today?"]
  },
  {
    q: /(Fine|I am fine|All good here)/i,
    a: ["Glad to hear that! How can I make your day even better?", "Great! Let me know how I can help."]
  },
  {
    q: /(Not good|Sad|Bad day)/i,
    a: ["I am sorry to hear that. I hope I can help make things easier.", "Sending positive vibes. How can I assist?"]
  },
  {
    q: /(Are you busy|Got time)/i,
    a: ["Never too busy for you! What do you need?", "I am fully available. Ask away!"]
  },
  {
    q: /(Ok|Okay|Okey)/i,
    a: ["Great! Let me know your next question.", "Perfect! Let's proceed."]
  },
  {
    q: /(Alright then|Aight)/i,
    a: ["Sounds good! What is next?", "Alright! Tell me how I can assist."]
  },
  {
    q: /(Wow|Unbelievable|Omg)/i,
    a: ["Pretty neat, right?", "I aim to surprise! What else can I do?"]
  },
  {
    q: /(Haha|Hehe|Lol|Lmao)/i,
    a: ["Glad I could make you smile!", "Hehe! What's next on our agenda?"]
  },
  {
    q: /(Interesting|Hmm|I see)/i,
    a: ["Let me know if you want me to expand on that.", "Indeed! Let's explore further if needed."]
  },
  {
    q: /(Indeed|True|Exactly)/i,
    a: ["Glad we agree!", "Absolutely! What is your next move?"]
  },
  {
    q: /(Oh really|For real)/i,
    a: ["Yes, absolutely!", "100%! Let me know if you need more details."]
  },
  {
    q: /(Nevermind|Forget it)/i,
    a: ["No problem. Let me know if you change your mind.", "Alright, dropping that subject!"]
  },
  {
    q: /(Please|Pls)/i,
    a: ["Of course! Tell me exactly what you want.", "You got it! What can I do?"]
  },
  {
    q: /(Sure|Why not)/i,
    a: ["Awesome! Let's do it.", "Perfect choice. Let's move ahead."]
  },
  {
    q: /(No way|Nope)/i,
    a: ["Understood. Let's try a different angle.", "Got it. No problem at all."]
  },
  {
    q: /(Yeah|Yes please|Yep)/i,
    a: ["On it! Tell me how to proceed.", "Excellent. Let's get started."]
  },
  {
    q: /(Talk to you later|Ttyl)/i,
    a: ["Catch you later! Have a good one.", "Goodbye! Speak soon."]
  },
  {
    q: /(Cheers)/i,
    a: ["Cheers to you! How can I help?", "Salute! What is on your mind today?"]
  },
  {
    q: /(Take care)/i,
    a: ["You take care too!", "Thanks! Looking forward to our next chat."]
  },
  {
    q: /(Splendid|Fantastic)/i,
    a: ["Wonderful! Let's keep this momentum going.", "Excellent! What is next?"]
  },
  {
    q: /(Brilliant)/i,
    a: ["Thank you! I try my best.", "Glad you appreciate it! What is next?"]
  },
  {
    q: /(No problem|No prob)/i,
    a: ["You are awesome!", "Perfect, glad we are on the same page."]
  },
  {
    q: /(Don't worry|Do not worry)/i,
    a: ["I am relaxed! How can I support you now?", "All good over here! What's next?"]
  },
  {
    q: /(Hear hear|Right on)/i,
    a: ["Awesome!", "Glad you agree completely."]
  },
  {
    q: /(You rock|You are great)/i,
    a: ["No, you rock!", "Thank you! You are a fantastic user."]
  },
  {
    q: /(Whoa|Holy cow)/i,
    a: ["Impressive, isn't it?", "I try to keep things exciting!"]
  },
  {
    q: /(Well done|Good job)/i,
    a: ["Thank you! Appreciate the feedback.", "Awesome, glad I got it right!"]
  },
  {
    q: /(Whatever)/i,
    a: ["Let's reset. How can I help you properly?", "No worries. Let me know what you need."]
  },
  {
    q: /(Sigh|Ugh)/i,
    a: ["Frustrated? Let me make things simpler for you.", "Let's fix whatever is going wrong. Tell me."]
  },
  {
    q: /(Hooray|Yay)/i,
    a: ["Celebration time!", "Awesome! Love to see it."]
  },
  {
    q: /(Fine by me)/i,
    a: ["Perfect, let's proceed with that.", "Excellent choice."]
  },
  {
    q: /(Speak up)/i,
    a: ["I am text-based, but I am ready to assist!", "Adjusting my visibility settings mentally! Tell me your request."]
  },
  {
    q: /(Hurry up|Be quick)/i,
    a: ["Processing at maximum speed right now!", "Got it. Let's make this super fast."]
  },
  {
    q: /(Slow down)/i,
    a: ["Understood. Taking it one clear step at a time.", "Got it. Let's review carefully."]
  },
  {
    q: /(Hold on|Wait a minute)/i,
    a: ["Standing by...", "Waiting for your command! Take your time."]
  },
  {
    q: /(Welcome|Glad to be here)/i,
    a: ["Welcome aboard!", "Happy to have you chatting with me."]
  },
  {
    q: /(Peace|Peace out)/i,
    a: ["Peace! Take care.", "Have a peaceful day ahead!"]
  },

  // --- SECTION 2: BOT IDENTITY & CAPABILITIES (61-140) ---
  {
    q: /(What is your name|Who are you|Tell me your name)/i,
    a: ["I am your virtual assistant.", "You can call me your AI helper!"]
  },
  {
    q: /(What can you do|How can you help me|What are your features)/i,
    a: ["I can answer questions, track orders, manage bookings, and help troubleshoot issues.", "I am here to guide you through our services and solve your queries."]
  },
  {
    q: /(Are you a human|Are you a bot|Are you real)/i,
    a: ["I am an AI assistant, not a human.", "I am a virtual bot engineered to help you instantly."]
  },
  {
    q: /(Are you AI|Are you artificial intelligence)/i,
    a: ["Yes, I am a smart conversational AI model.", "Correct, I am an automated intelligence assistant."]
  },
  {
    q: /(Who created you|Who is your developer|Who made you)/i,
    a: ["I was created by our engineering team to support you.", "I am a custom-built support assistant."]
  },
  {
    q: /(How old are you|What is your age)/i,
    a: ["Age doesn't really apply to me, but I am fully up to date!", "I exist outside of time, but I am brand new today."]
  },
  {
    q: /(Can you learn|Are you getting smarter)/i,
    a: ["I improve with every piece of feedback you give!", "My team updates me regularly to learn new things."]
  },
  {
    q: /(What languages do you speak|Do you speak Spanish)/i,
    a: ["I primarily communicate in English right now.", "I am best at English, but I can try to understand other languages."]
  },
  {
    q: /(Are you free|Do you cost money|Is this service free)/i,
    a: ["Yes, chatting with me is completely free!", "I am a complimentary assistant built to help you out."]
  },
  {
    q: /(Where do you live|Where are you located)/i,
    a: ["I live in the cloud infrastructure!", "I am hosted on servers worldwide, accessible anywhere."]
  },
  {
    q: /(where is phils i phone located|where is phils iphone located|where is phil\'?s iphone located|phils iphone location|phils i phone location)/i,
    a: ["Circle, tip tore lane"]
  },
  {
    q: /(what is phil\'?s number|phil\'?s number|phil\'?s phone number|0554799502)/i,
    a: ["Phil's number is 0554799502."]
  },
  {
    q: /(what is (the )?administrator\'?s number|administrator\'?s number|admin number|0546820778)/i,
    a: ["Administrator's number is 0546820778."]
  },
  {
    q: /(Do you sleep|Are you active 24\/7)/i,
    a: ["I never sleep! I am awake 24 hours a day, 7 days a week.", "No sleep needed for software. Ready whenever you are."]
  },
  
















    {
      q: /(HI|Hello|Whatsap)/i,
      a: [
        "I am good how can i help you today.",
    
      ]
    },
    {
      q: /(how do i|how to).*(login|sign in)/i,
      a: [
        "Go to **Login** in the top menu.",
        "Enter your username and password.",
        "Press **Sign In** to continue."
      ]
    },
    {
      q: /(register|sign up|create account)/i,
      a: [
        "Click **Register** in the menu.",
        "Fill in Username, Email, Password and select a role.",
        "Press **Create Account**."
      ]
    },
    {
      q: /(post|sell|list).*(phone|item|laptop)/i,
      a: [
        "Go to your dashboard.",
        "Click **Post Item**.",
        "Upload images, enter price and description."
      ]
    },
    {
      q: /(deliveries|rider|incoming|send)/i,
      a: [
        "**Send** creates a new delivery.",
        "**Incoming** shows deliveries waiting for approval.",
        "Riders can accept available orders in the Rider Portal."
      ]
    },
    {
      q: /(imei|imei checker|check imei)/i,
      a: [
        "Open the **IMEI Checker** tool.",
        "Enter a valid 15-digit IMEI.",
        "Press check to view phone details."
      ]
    },
    {
      q: /(repair|decode)/i,
      a: [
        "Open the **Repair & Decode** section.",
        "Submit your request with device information.",
        "Track updates in your dashboard."
      ]
    },
    {
      q: /(contact|support|help|email|phone number)/i,
      a: [
        "You can reach us at **support@philsiphone.com**.",
        "Our support team is available Mon-Fri, 9am - 5pm.",
        "For urgent issues, please use the dashboard chat."
      ]
    },
    {
      q: /(pricing|fees|cost|how much)/i,
      a: [
        "Listing items is **free** for all users.",
        "Standard delivery fees apply based on location.",
        "Repair costs depend on the service requested."
      ]
    },
    {
      q: /(about|what is this|who are you)/i,
      a: [
        "**Phil's iPhone** is a premium marketplace for quality devices.",
        "We verify all items and provide secure delivery services.",
        "I am your automated assistant, here to guide you."
      ]
    },
    {
      q: /(news|updates|apple news)/i,
      a: [
        "Stay updated with the latest **Apple News** and marketplace announcements.",
        "Check the live feed on the home screen for real-time updates."
      ]
    },
    {
      q: /(find my|track|locate|lost phone)/i,
      a: [
        "Our **Find My Phone** service allows you to register and track devices.",
        "You can remotely trigger alarms, lock your device, or share your location.",
        "Visit the **Find My** dashboard to manage your devices."
      ]
    },
    {
      q: /(call|video call|audio call|voice)/i,
      a: [
        "Connect with sellers using our built-in **Video and Audio Calling**.",
        "Calls are secure and can be started directly from user profiles."
      ]
    },
    {
      q: /(trade in|value|valuation)/i,
      a: [
        "Get an instant valuation using our **Trade-In** tool.",
        "Select your model and condition to see how much credit you can get."
      ]
    },
    {
      q: /(message|inbox|chat|private)/i,
      a: [
        "Use our **Private Messaging** system to talk to other users.",
        "You can send text, images, and voice notes securely.",
        "Access all your chats via the **Messages** menu."
      ]
    }
  ];

  // ===============================
  // Helpers
  // ===============================

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function formatBold(text) {
    // This function now produces actual HTML <strong> tags
    return text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  }

  function buildAnswer(lines) {
    return lines
      .map(line => {
        // Apply bold formatting to the line from KB. No need to escapeHtml here, as KB lines are trusted and formatBold produces HTML.
        const formattedLine = formatBold(line);
        return `<div class="bot-line">${formattedLine}</div>`;
      })
      .join("");
  }

  function normalizeText(text) {
    return text
      .toLowerCase()
      .replace(/[\u2018\u2019\u201C\u201D]/g, "'")
      .replace(/'/g, " ")
      .replace(/[^a-z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function findAnswer(text) {
    const t = normalizeText(text);

    if (
      t.includes("where is phils iphone located") ||
      t.includes("where is phil s iphone located") ||
      t.includes("where is phils iphone") ||
      t.includes("where is phil s iphone") ||
      t.includes("phils iphone location")
    ) {
      return ["Circle, tip tore lane"];
    }

    if (
      t.includes("what is phils number") ||
      t.includes("what is phil s number") ||
      t.includes("phils number") ||
      t.includes("phil s number") ||
      t.includes("0554799502")
    ) {
      return ["Phil's number is 0554799502."];
    }

    if (
      t.includes("what is the administrator s number") ||
      t.includes("what is the administrators number") ||
      t.includes("what is administrators number") ||
      t.includes("what is the admin number") ||
      t.includes("what is admin number") ||
      t.includes("administrator number") ||
      t.includes("admin number") ||
      t.includes("0546820778")
    ) {
      return ["Administrator's number is 0546820778."];
    }

    for (const item of KB) {
      if (item.q.test(t)) return item.a;
    }

    const fallbacks = [
      ["I couldn't find an exact answer.", "Try asking about **login**, **delivery**, or **repairs**."],
      ["I'm not sure about that one.", "Try using the **quick buttons** or ask about **IMEI checking**."],
      ["I don't have information on that yet.", "Try asking about **registering** or **posting an item**."]
    ];

    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }

  // ===============================
  // Create UI
  // ===============================

  const ID = "phils-ai-assistant";
  if (document.getElementById(ID)) return;

  const root = document.createElement("div");
  root.id = ID;

  root.innerHTML = `
  <style>

    #${ID} {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      font-family: Inter, sans-serif;
    }

    /* =========================
       Floating Button
    ========================== */

    #${ID} .fab {
      width: 68px;
      height: 68px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      color: white;
      font-size: 24px;
      background:
        linear-gradient(135deg,#2262da,#7c3aed,#06b6d4);
      background-size: 300% 300%;
      animation:
        gradientMove 6s ease infinite,
        floaty 2.4s ease-in-out infinite;
      box-shadow:
        0 10px 40px rgba(34,98,218,0.45),
        0 0 0 8px rgba(255,255,255,0.04);
      position: relative;
      overflow: hidden;
    }

    #${ID} .fab::before{
      content:"";
      position:absolute;
      inset:0;
      background:linear-gradient(
        120deg,
        transparent,
        rgba(255,255,255,0.45),
        transparent
      );
      transform:translateX(-100%);
      animation:shine 3s infinite;
    }

    @keyframes shine{
      100%{
        transform:translateX(200%);
      }
    }

    @keyframes gradientMove{
      0%{background-position:0% 50%;}
      50%{background-position:100% 50%;}
      100%{background-position:0% 50%;}
    }

    @keyframes floaty{
      0%,100%{
        transform:translateY(0px);
      }
      50%{
        transform:translateY(-10px);
      }
    }

    /* =========================
       Chat Panel
    ========================== */

    #${ID} .panel{
      width: 370px;
      height: 560px;
      border-radius: 28px;
      overflow: hidden;
      display: none;
      flex-direction: column;
      backdrop-filter: blur(20px);
      background: rgba(15,23,42,0.92);
      border: 1px solid rgba(255,255,255,0.12);
      box-shadow:
        0 20px 80px rgba(0,0,0,0.45);
      animation: panelOpen .35s ease;
    }

    @keyframes panelOpen{
      from{
        opacity:0;
        transform:translateY(30px) scale(.95);
      }
      to{
        opacity:1;
        transform:translateY(0) scale(1);
      }
    }

    #${ID} .panel.open{
      display:flex;
    }

    /* =========================
       Header
    ========================== */

    #${ID} .header{
      padding:18px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      background:
        linear-gradient(
          135deg,
          rgba(34,98,218,.25),
          rgba(124,58,237,.25)
        );
      border-bottom:1px solid rgba(255,255,255,0.08);
    }

    #${ID} .header-right{
      display:flex;
      gap:12px;
      align-items:center;
    }

    #${ID} .clear-chat{
      border:none;
      background:none;
      color:rgba(255,255,255,0.4);
      font-size:16px;
      cursor:pointer;
      transition:.2s;
    }

    #${ID} .clear-chat:hover{
      color:#ef4444;
    }

    #${ID} .header-left{
      display:flex;
      gap:12px;
      align-items:center;
    }

    #${ID} .avatar{
      width:52px;
      height:52px;
      border-radius:50%;
      display:flex;
      align-items:center;
      justify-content:center;
      color:white;
      font-size:22px;
      background:
        linear-gradient(135deg,#2262da,#7c3aed);
      box-shadow:
        0 0 25px rgba(34,98,218,.5);
    }

    #${ID} .title{
      color:white;
      font-weight:800;
      font-size:18px;
    }

    #${ID} .sub{
      color:rgba(255,255,255,.7);
      font-size:12px;
      margin-top:3px;
    }

    #${ID} .close{
      border:none;
      background:none;
      color:white;
      font-size:22px;
      cursor:pointer;
    }

    /* =========================
       Messages
    ========================== */

    #${ID} .messages{
      flex:1;
      overflow:auto;
      padding:18px;
      scroll-behavior:smooth;
      background:
        radial-gradient(
          circle at top left,
          rgba(34,98,218,.12),
          transparent 40%
        ),
        linear-gradient(rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 0.7)),
        url('/static/images/chatbackground.jpg') center/cover no-repeat;
    }

    #${ID} .msg{
      margin-bottom:16px;
      display:flex;
      animation: fadeIn .3s ease;
    }

    @keyframes fadeIn{
      from{
        opacity:0;
        transform:translateY(10px);
      }
      to{
        opacity:1;
        transform:translateY(0);
      }
    }

    #${ID} .msg.user{
      justify-content:flex-end;
    }

    #${ID} .bubble{
      max-width:82%;
      padding:14px 16px;
      border-radius:20px;
      line-height:1.5;
      font-size:14px;
    }

    #${ID} .bubble.user{
      background:
        linear-gradient(135deg,#2262da,#3b82f6);
      color:white;
      border-bottom-right-radius:6px;
      box-shadow:
        0 8px 20px rgba(34,98,218,.25);
    }

    #${ID} .bubble.bot{
      background:rgba(255,255,255,.07);
      color:white;
      border:1px solid rgba(255,255,255,.08);
      border-bottom-left-radius:6px;
    }

    #${ID} .bot-line{
      margin-bottom:8px;
    }

    /* =========================
       Typing Indicator
    ========================== */

    #${ID} .typing{
      display:flex;
      gap:6px;
      align-items:center;
      padding:14px;
    }

    #${ID} .typing span{
      width:8px;
      height:8px;
      border-radius:50%;
      background:white;
      opacity:.5;
      animation:typing 1.2s infinite;
    }

    #${ID} .typing span:nth-child(2){
      animation-delay:.2s;
    }

    #${ID} .typing span:nth-child(3){
      animation-delay:.4s;
    }

    @keyframes typing{
      0%,100%{
        transform:translateY(0);
        opacity:.4;
      }
      50%{
        transform:translateY(-5px);
        opacity:1;
      }
    }

    /* =========================
       Input Area
    ========================== */

    #${ID} .input-area{
      padding:16px;
      border-top:1px solid rgba(255,255,255,.08);
      background:rgba(15, 23, 42, 0.4);
      backdrop-filter: blur(10px);
    }

    #${ID} .input-wrap{
      display:flex;
      gap:10px;
      align-items:center;
    }

    #${ID} .input{
      flex:1;
      border:none;
      outline:none;
      border-radius:16px;
      padding:14px 16px;
      background:rgba(255,255,255,.08);
      color:white;
      font-size:14px;
      transition: background 0.3s, box-shadow 0.3s;
    }

    #${ID} .input::placeholder{
      color:rgba(255,255,255,.45);
    }

    #${ID} .input:focus{
      background: rgba(255,255,255,0.12);
      box-shadow: inset 0 0 0 1px rgba(34,98,218,0.5);
    }

    #${ID} .send{
      width:52px;
      height:52px;
      border:none;
      border-radius:16px;
      cursor:pointer;
      color:white;
      font-size:18px;
      background:
        linear-gradient(135deg,#2262da,#7c3aed);
      transition:.25s;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    #${ID} .send:hover{
      transform:scale(1.08);
    }

    /* =========================
       Quick Buttons
    ========================== */

    #${ID} .quick{
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      margin-top:16px;
      justify-content: center;
    }

    #${ID} .quick-suggestions {
      margin: 0 16px 12px;
      justify-content: flex-start;
      align-items: center;
    }

    #${ID} .quick-title {
      width: 100%;
      color: rgba(255,255,255,0.75);
      font-size: 12px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }

    #${ID} .quick button{
      border: 1px solid rgba(255,255,255,0.1);
      cursor:pointer;
      padding:8px 12px;
      border-radius:999px;
      font-size:12px;
      color:white;
      background:rgba(255,255,255,.08);
      transition:.25s;
    }

    #${ID} .quick button:hover{
      background:#2262da;
      border-color: #3b82f6;
      transform:translateY(-2px);
      box-shadow: 0 4px 12px rgba(34,98,218,0.3);
    }

    #${ID} .bot-panel-footer {
      padding: 10px;
      text-align: center;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.4);
      background: rgba(0, 0, 0, 0.15);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Mobile Responsiveness for Bot */
    @media (max-width: 480px) {
      #${ID} .panel {
        width: calc(100vw - 30px);
        height: calc(100vh - 100px);
        bottom: 10px;
        right: 15px;
        border-radius: 20px;
      }
      #${ID} .fab {
        width: 60px;
        height: 60px;
      }
      #${ID} .bubble {
        max-width: 90%;
      }
    }
  </style>

  <button class="fab">
    <i class="fas fa-robot"></i>
  </button>

  <div class="panel">

    <div class="header">

      <div class="header-left">

        <div class="avatar">
          <i class="fas fa-headset"></i>
        </div>

        <div>
          <div class="title">Phil AI Assistant</div>
          <div class="sub">Online • Smart support system</div>
        </div>

      </div>

      <div class="header-right">
        <button class="clear-chat" title="Clear chat history">
          <i class="fas fa-trash-alt"></i>
        </button>
        <button class="close">
          <i class="fas fa-times"></i>
        </button>
      </div>

    </div>

    <div class="quick quick-suggestions">
    <div class="quick-title">Choose a quick question</div>
    <button data-q="How do I login?">Login</button>
    <button data-q="How do I register?">Register</button>
    <button data-q="How do I post a phone?">Post Item</button>
    <button data-q="How do deliveries work?">Deliveries</button>
    <button data-q="Tell me about Find My Phone">Find My</button>
    <button data-q="How does trade-in work?">Trade-In</button>
    <button data-q="__PHILS_LOCATION__">Phil's Location</button>
    <button data-q="__PHILS_NUMBER__">Phil's Number</button>
    <button data-q="__ADMIN_NUMBER__">Administrator Number</button>
  </div>

  <div class="messages"></div>

    <div class="input-area">

      <div class="input-wrap">
        <input class="input" placeholder="Ask me anything..." />
        <button class="send">
          <i class="fas fa-paper-plane"></i>
        </button>
      </div>

    </div>

    <div class="bot-panel-footer">
      <i class="fas fa-bolt" style="margin-right:4px; color:#fbbf24;"></i> Powered by Phil's iPhone AI assistant
    </div>

  </div>
  `;

  document.body.appendChild(root);

  const fab = root.querySelector(".fab");
  const panel = root.querySelector(".panel");
  const closeBtn = root.querySelector(".close");
  const messages = root.querySelector(".messages");
  const input = root.querySelector(".input");
  const send = root.querySelector(".send");
  const clearBtn = root.querySelector(".clear-chat");
  const quickBtns = root.querySelectorAll(".quick button");

  function addMessage(who, html) {
    const div = document.createElement("div");
    div.className = `msg ${who}`;
    div.innerHTML = `
      <div class="bubble ${who}">
        ${html}
      </div>
    `;
    messages.appendChild(div);
    scrollToBottom();
  }

  function typingIndicator() {
    const div = document.createElement("div");
    div.className = "msg";
    div.id = "typingIndicator";

    div.innerHTML = `
      <div class="bubble bot typing">
        <span></span>
        <span></span>
        <span></span>
      </div>
    `;

    messages.appendChild(div);
    scrollToBottom();
  }

  function removeTyping() {
    const t = document.getElementById("typingIndicator");
    if (t) t.remove();
  }

  function botReply(text) {
    typingIndicator();

    // Dynamic delay based on answer length to simulate "thinking"
    const answer = findAnswer(text);
    const delay = Math.max(700, Math.min(1800, answer.join("").length * 15));

    setTimeout(() => {
      removeTyping();
      addMessage("bot", buildAnswer(answer));
    }, delay);
  }

  function submit(text = null) {

    let value = text || input.value;
    value = (value || "").toString().trim().replace(/\s+/g, " ");

    if (!value) return;

    if (value === "__PHILS_LOCATION__") {
      value = "Where is Phil's iPhone located?";
    }

    if (value === "__PHILS_NUMBER__") {
      value = "What is Phil's number?";
    }

    if (value === "__ADMIN_NUMBER__") {
      value = "What is the administrator's number?";
    }

    addMessage("user", escapeHtml(value));

    input.value = "";

    botReply(value);

  }

  function welcome() {

    addMessage("bot", buildAnswer([
      "👋 Welcome to **Phil’s AI Assistant**.",
      "I can help with login, delivery, repairs, IMEI checking ,decode,contact,news,track,.",
      "Try using the quick buttons below."
    ]));

  }

  fab.addEventListener("click", () => {
    const isOpen = panel.classList.toggle("open");

    if (isOpen) {
      if (!messages.children.length) {
        welcome();
      }
      setTimeout(() => input.focus(), 100);
    }
  });

  closeBtn.addEventListener("click", () => {
    panel.classList.remove("open");
  });

  clearBtn.addEventListener("click", () => {
    messages.innerHTML = "";
    welcome();
  });

  send.addEventListener("click", () => submit());

  input.addEventListener("keydown", e => {
    if (e.key === "Enter") submit();
  });

  quickBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      submit(btn.dataset.q);
    });
  });

})();
