const API = "http://127.0.0.1:5000";

// ---------- REGISTER ----------
async function register() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!email || !password) {
    alert("Please fill all fields");
    return;
  }

  try {
    const res = await fetch(`${API}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      alert("Registered successfully! Please login.");
      location.href = "login.html";
    } else if (res.status === 409) {
      alert("User already exists");
    } else {
      alert(data.message || "Something went wrong");
    }
  } catch (err) {
    alert("Network error: Is the backend running?");
  }
}

// ---------- LOGIN ----------
async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!email || !password) {
    alert("Please fill all fields");
    return;
  }

  try {
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem("user", JSON.stringify(data));
      location.href = "dashboard.html";
    } else {
      alert("Invalid credentials");
    }
  } catch (err) {
    alert("Network error: Is the backend running?");
  }
}

// ---------- LOGOUT ----------
function logout() {
  localStorage.removeItem("user");
  location.href = "index.html";
}