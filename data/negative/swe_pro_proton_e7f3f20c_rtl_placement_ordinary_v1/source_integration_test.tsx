import { useState } from 'react';

import { render, waitFor } from '@testing-library/react';

import { PopperPlacement } from './interface';
import usePopper from './usePopper';
import { allPopperPlacements, getPhysicalPlacement } from './utils';

describe('physical Popper placement', () => {
    test.each(allPopperPlacements)('LTR preserves %s', (placement) => {
        expect(getPhysicalPlacement(placement, false)).toBe(placement);
    });
    test.each([
        ['top-start', 'top-end'],
        ['top-end', 'top-start'],
        ['bottom-start', 'bottom-end'],
        ['bottom-end', 'bottom-start'],
        ['top', 'top'],
        ['bottom', 'bottom'],
        ['left', 'left'],
        ['right', 'right'],
        ['left-start', 'left-start'],
        ['left-end', 'left-end'],
        ['right-start', 'right-start'],
        ['right-end', 'right-end'],
    ])('RTL exposes %s as %s', (placement, expected) => {
        expect(getPhysicalPlacement(placement as PopperPlacement, true)).toBe(expected);
    });
    beforeEach(() => {
        Object.defineProperty(document.documentElement, 'clientWidth', { configurable: true, value: 2000 });
        Object.defineProperty(document.documentElement, 'clientHeight', { configurable: true, value: 2000 });
        jest.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function () {
            const anchor = this.dataset.testid === 'anchor';
            const x = anchor ? 500 : 0,
                y = anchor ? 500 : 0;
            const width = anchor ? 100 : 20,
                height = anchor ? 40 : 10;
            return { x, y, left: x, top: y, right: x + width, bottom: y + height, width, height, toJSON: () => ({}) };
        });
        jest.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockImplementation(function () {
            return this.dataset.testid === 'anchor' ? 100 : 20;
        });
        jest.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockImplementation(function () {
            return this.dataset.testid === 'anchor' ? 40 : 10;
        });
    });
    afterEach(() => jest.restoreAllMocks());
    test.each([
        ['ltr', 'top-start', 'top-start', 500],
        ['rtl', 'top-start', 'top-end', 580],
        ['ltr', 'top-end', 'top-end', 580],
        ['rtl', 'top-end', 'top-start', 500],
        ['ltr', 'bottom-start', 'bottom-start', 500],
        ['rtl', 'bottom-start', 'bottom-end', 580],
        ['ltr', 'bottom-end', 'bottom-end', 580],
        ['rtl', 'bottom-end', 'bottom-start', 500],
    ])('native hook %s %s reports %s at x=%s', async (direction, placement, expected, expectedX) => {
        const Component = () => {
            const [anchor, setAnchor] = useState<HTMLElement | null>(null);
            const popper = usePopper({
                isOpen: true,
                originalPlacement: placement as PopperPlacement,
                availablePlacements: [placement as PopperPlacement],
                reference: { mode: 'element', value: anchor },
            });
            return (
                <>
                    <button ref={setAnchor} data-testid="anchor">
                        anchor
                    </button>
                    <div
                        ref={popper.floating}
                        data-testid="floating"
                        style={{ direction, width: 20, height: 10, position: 'fixed' }}
                    >
                        <span data-testid="placement">{popper.placement}</span>
                        <span data-testid="x">{popper.position.left}</span>
                    </div>
                </>
            );
        };
        const { getByTestId, unmount } = render(<Component />);
        await waitFor(() => {
            expect(getByTestId('placement').textContent).toBe(expected);
            expect(Number(getByTestId('x').textContent)).toBe(expectedX);
        });
        console.log(
            'Native placement:',
            direction,
            placement,
            getByTestId('placement').textContent,
            'x=',
            getByTestId('x').textContent
        );
        unmount();
    });
});
