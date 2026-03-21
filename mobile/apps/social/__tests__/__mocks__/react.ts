// Mock React for testing without Expo/RN runtime
const createElement = jest.fn(
  (type: any, props: any, ...children: any[]) => ({
    type,
    props: { ...props, children: children.length === 1 ? children[0] : children },
  })
);

const useEffect = jest.fn((fn: Function) => fn());
const useState = jest.fn((initial: any) => [initial, jest.fn()]);
const useRef = jest.fn((initial: any) => ({ current: initial }));
const useCallback = jest.fn((fn: Function) => fn);
const useMemo = jest.fn((fn: Function) => fn());

module.exports = {
  default: { createElement, useEffect, useState, useRef, useCallback, useMemo },
  createElement,
  useEffect,
  useState,
  useRef,
  useCallback,
  useMemo,
};
