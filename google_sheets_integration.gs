function COMPANY_INTEL(company, question) {
  const API_KEYS = {
    SERPAPI: "<YOUR_SERP_API>",
    GROQ: "<YOUR_GROQ_API>"
  };

  try {
    // 1. Get Search Results
    const searchResults = UrlFetchApp.fetch(`https://serpapi.com/search?q=${encodeURIComponent(question + " " + company)}&api_key=${API_KEYS.SERPAPI}&engine=google&google_domain=google.com&gl=us&hl=en&num=5`);
    const organicResults = JSON.parse(searchResults.getContentText()).organic_results.slice(0, 5);

    // 2. Format Context
    const context = organicResults.map(result => 
      `Title: ${result.title?.substring(0,100) || ''}\nLink: ${result.link || ''}\nSnippet: ${result.snippet?.substring(0,100) || ''}`
    ).join("\n\n");

    // 3. Create AI Prompt
    const prompt = `Instructions:
    - Answer in 2-3 words max
    - Choose first result if multiple answers exist
    - Say "I DONT KNOW" if uncertain

    Company: ${company}
    Question: ${question}
    Context: ${context}`;

    // 4. Get Groq Response
    const groqResponse = UrlFetchApp.fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "post",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEYS.GROQ}`
      },
      payload: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{role: "user", content: prompt}],
        temperature: 0.1,
        max_tokens: 50
      })
    });

    // 5. Process Response
    const response = JSON.parse(groqResponse.getContentText()).choices[0].message.content;
    return response.split("Answer:")[1]?.trim().replace(/"/g, '') || "I DONT KNOW";

  } catch(e) {
    return "Error: " + e.toString();
  }
}