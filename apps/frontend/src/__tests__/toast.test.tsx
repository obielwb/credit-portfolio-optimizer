import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import { ToastContainer, type ToastMessage } from "@/components/toast";

function makeToast(overrides?: Partial<ToastMessage>): ToastMessage {
  return {
    id: "test-id-1",
    variant: "success",
    title: "Operation completed",
    description: "The data was saved successfully.",
    ...overrides,
  };
}

describe("ToastContainer", () => {
  it("renders nothing when toasts array is empty", () => {
    const { container } = render(<ToastContainer toasts={[]} onDismiss={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a toast with title and description", () => {
    const toast = makeToast();
    render(<ToastContainer toasts={[toast]} onDismiss={() => {}} />);

    expect(screen.getByText("Operation completed")).toBeInTheDocument();
    expect(screen.getByText("The data was saved successfully.")).toBeInTheDocument();
  });

  it("calls onDismiss with the toast id when close button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = jest.fn();
    const toast = makeToast();

    render(<ToastContainer toasts={[toast]} onDismiss={onDismiss} />);

    await user.click(screen.getByRole("button", { name: /dismiss notification/i }));
    expect(onDismiss).toHaveBeenCalledWith("test-id-1");
  });

  it("renders multiple toasts", () => {
    const toasts: ToastMessage[] = [
      makeToast({ id: "a", title: "Primeiro" }),
      makeToast({ id: "b", title: "Segundo", variant: "error" }),
      makeToast({ id: "c", title: "Terceiro", variant: "warning" }),
    ];

    render(<ToastContainer toasts={toasts} onDismiss={() => {}} />);

    expect(screen.getByText("Primeiro")).toBeInTheDocument();
    expect(screen.getByText("Segundo")).toBeInTheDocument();
    expect(screen.getByText("Terceiro")).toBeInTheDocument();
  });

  it("renders error toast with role=alert", () => {
    const toast = makeToast({ variant: "error", title: "Upload error" });
    render(<ToastContainer toasts={[toast]} onDismiss={() => {}} />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
  });

  it("calls onDismiss after 5 seconds (auto-dismiss)", async () => {
    jest.useFakeTimers();
    const onDismiss = jest.fn();
    const toast = makeToast();

    render(<ToastContainer toasts={[toast]} onDismiss={onDismiss} />);

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(onDismiss).toHaveBeenCalledWith("test-id-1");
    jest.useRealTimers();
  });

  it("renders toast without description when not provided", () => {
    const toast = makeToast({ description: undefined });
    render(<ToastContainer toasts={[toast]} onDismiss={() => {}} />);

    expect(screen.getByText("Operation completed")).toBeInTheDocument();
    expect(screen.queryByText(/Os data foram/)).not.toBeInTheDocument();
  });
});
