"use client";






import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  type ReactNode,
} from "react";

import { ToastContainer, type ToastMessage, type ToastVariant } from "@/components/toast";
import { ApiResponseError } from "@/lib/types";



const API_ERROR_MESSAGES: Record<string, string> = {
  INVALID_FILE_EXTENSION:
    "Invalid file format. Use .csv or .parquet files only.",
  EMPTY_FILE: "The uploaded file is empty. Check its contents and try again.",
  INVALID_ALGORITHM:
    "Unknown algorithm. Valid options are \"simplex\", \"simplex_ortools\", and \"branch_bound\".",
  MISSING_REQUIRED_PARAMETERS:
    "Required parameters are missing. Complete every indicated field.",
  RUN_NOT_FOUND:
    "Run not found. Check the identifier or start a new analysis.",
  RESULT_NOT_FOUND:
    "A result is not available for this run. Analysis may still be in progress.",
  PARAMETERS_NOT_FOUND:
    "Parameter configuration not found. Create the parameters before continuing.",
  NETWORK_ERROR:
    "Could not connect to the server. Confirm that the backend is running at http://localhost:8000.",
};







export function getApiErrorMessage(err: unknown): string {
  if (err instanceof ApiResponseError) {
    return API_ERROR_MESSAGES[err.code] ?? err.message;
  }
  if (err instanceof TypeError && err.message.toLowerCase().includes("fetch")) {
    return API_ERROR_MESSAGES["NETWORK_ERROR"];
  }
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred. Try again.";
}

// ── State / reducer ───────────────────────────────────────────────────────────

type ToastAction =
  | { type: "ADD"; toast: ToastMessage }
  | { type: "DISMISS"; id: string };


function reducer(state: ToastMessage[], action: ToastAction): ToastMessage[] {
  switch (action.type) {
    case "ADD":
      return [...state, action.toast];
    case "DISMISS":
      return state.filter((t) => t.id !== action.id);
    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────────────────────

interface ToastContextValue {
  toast: (opts: { variant: ToastVariant; title: string; description?: string }) => void;
  toastError: (err: unknown, title?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);







export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, dispatch] = useReducer(reducer, []);

  const toast = useCallback(
    ({
      variant,
      title,
      description,
    }: {
      variant: ToastVariant;
      title: string;
      description?: string;
    }) => {
      dispatch({
        type: "ADD",
        toast: {
          id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          variant,
          title,
          description,
        },
      });
    },
    [],
  );

  const toastError = useCallback(
    (err: unknown, title = "Erro") => {
      dispatch({
        type: "ADD",
        toast: {
          id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          variant: "error",
          title,
          description: getApiErrorMessage(err),
        },
      });
    },
    [],
  );

  const dismiss = useCallback((id: string) => {
    dispatch({ type: "DISMISS", id });
  }, []);

  return (
    <ToastContext.Provider value={{ toast, toastError, dismiss }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}







export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
