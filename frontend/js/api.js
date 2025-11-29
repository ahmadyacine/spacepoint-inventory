// frontend/js/api.js
const API_BASE = "http://127.0.0.1:8000";

function getToken() {
    return sessionStorage.getItem("token");
}

function getRole() {
    return sessionStorage.getItem("role");
}

function getUsername() {
    return sessionStorage.getItem("username");
}

function getInstructorId() {
    return sessionStorage.getItem("instructor_id");
}

function setAuth(token, role, username, instructorId = null) {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("role", role);
    sessionStorage.setItem("username", username);
    if (instructorId) {
        sessionStorage.setItem("instructor_id", instructorId);
    }
}

function clearAuth() {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("role");
    sessionStorage.removeItem("username");
    sessionStorage.removeItem("instructor_id");
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = options.headers || {};
    headers["Content-Type"] = "application/json";
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    }

    const res = await fetch(API_BASE + path, {
        ...options,
        headers,
    });

    if (res.status === 401) {
        // Unauthorized - redirect to login
        clearAuth();
        window.location.href = "login.html";
        throw new Error("Unauthorized");
    }

    if (!res.ok) {
        let msg = "API error";
        try {
            const data = await res.json();
            msg = data.detail || JSON.stringify(data);
        } catch (e) {
            // Ignore JSON parsing errors
        }
        throw new Error(msg);
    }

    return res.json();
}