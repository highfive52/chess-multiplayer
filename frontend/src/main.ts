// frontend/src/main.ts
import { io } from "socket.io-client";

console.log("TypeScript environment is up and running!");

// Connect to your future backend loop
const socket = io("http://localhost:8000");

socket.on("connect", () => {
  console.log("Connected to the server successfully! Socket ID:", socket.id);
});
