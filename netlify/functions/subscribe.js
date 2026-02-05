// netlify/functions/subscribe.js
// Serverless proxy for MailerLite API — keeps API key off the client

exports.handler = async (event) => {
  // Only allow POST
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Method not allowed" }),
    };
  }

  // CORS headers (adjust origin for production)
  const headers = {
    "Access-Control-Allow-Origin": "https://screamingfixes.com",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };

  // Handle preflight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers, body: "" };
  }

  try {
    const { email } = JSON.parse(event.body);

    // Validate email
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: "Invalid email address" }),
      };
    }

    // Simple honeypot check — if a "website" field is filled, it's a bot
    const { website } = JSON.parse(event.body);
    if (website) {
      // Pretend success to the bot
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true }),
      };
    }

    const API_KEY = process.env.MAILERLITE_API_KEY;
    if (!API_KEY) {
      console.error("MAILERLITE_API_KEY environment variable not set");
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: "Server configuration error" }),
      };
    }

    const GROUP_ID = "178597163422450957";

    // Call MailerLite API
    const response = await fetch(
      "https://connect.mailerlite.com/api/subscribers",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${API_KEY}`,
        },
        body: JSON.stringify({
          email: email,
          groups: [GROUP_ID],
          status: "active",
        }),
      }
    );

    const data = await response.json();

    if (response.ok) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true }),
      };
    }

    // MailerLite returns 422 for already-subscribed emails
    if (response.status === 422 || response.status === 409) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          success: true,
          message: "Already subscribed",
        }),
      };
    }

    console.error("MailerLite error:", response.status, data);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: "Subscription failed" }),
    };
  } catch (err) {
    console.error("Function error:", err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: "Server error" }),
    };
  }
};
