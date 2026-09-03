import { expect } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";

// Register the jest-dom matchers with Vitest's expect
expect.extend(matchers as unknown as Record<string, any>);

export {};
import "@testing-library/jest-dom/vitest";
